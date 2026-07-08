from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from app.knowledge.chunker import chunk_document
from app.knowledge.formatter import canonical_json
from app.knowledge.models import (
    Category,
    IngestionResult,
    IngestionStatus,
    SourceType,
    VerificationStatus,
    utc_now_iso,
)
from app.knowledge.repository import KnowledgeRepository, sha256_hex
from app.security.secrets import redact
from app.services.tenant_resolver import TenantContext


class IngestionError(Exception):
    """Non-fatal ingestion failure (job marked failed, safe message stored)."""


def _safe_message(exc: Exception) -> str:
    """Store a safe error message with secrets redacted."""
    return redact(str(exc))[:500]


def _is_indexable(status: str, guest_visible: bool, internal_only: bool) -> bool:
    """Only verified + published + guest-visible + non-internal may be indexed."""
    return (
        status == VerificationStatus.VERIFIED.value
        and guest_visible
        and not internal_only
    )


def build_embedded_points(
    ctx: TenantContext,
    *,
    document_id: str,
    version_row: dict[str, Any],
    category: str,
    checksum: str,
    chunks: list[Any],
    vectors: list[list[float]],
    source_filename: str | None,
    published_at: str,
) -> list[dict[str, Any]]:
    """Build Qdrant points with the COMPLETE guest-safety payload.

    Every point carries tenant scoping, the exact immutable version, and the
    publication metadata (`published` + `published_at`) that retrieval filters
    on. Shared by the ingestion (seed) path and the admin publish path so the
    payload contract lives in exactly one place.
    """
    points: list[dict[str, Any]] = []
    for c, vec in zip(chunks, vectors, strict=True):
        points.append(
            {
                "id": f"{version_row['id']}-{c.chunk_index}",
                "vector": vec,
                "payload": {
                    "tenant_id": ctx.tenant_id,
                    "tenant_slug": ctx.tenant_slug,
                    "document_id": document_id,
                    "document_version_id": version_row["id"],
                    "category": category,
                    "version": version_row["version"],
                    "checksum": checksum,
                    "verification_status": VerificationStatus.VERIFIED.value,
                    "guest_visible": True,
                    "internal_only": False,
                    "published": True,
                    "published_at": published_at,
                    "chunk_index": c.chunk_index,
                    "source_filename": source_filename,
                    "text": c.text,
                },
            }
        )
    return points


class IngestionService:
    """Multi-tenant knowledge ingestion pipeline.

    Deterministic and idempotent. On failure it marks the job failed with a SAFE
    message (no secrets), and never leaves a version falsely marked indexed.
    """

    def __init__(
        self,
        repository: KnowledgeRepository,
        *,
        embedder: Any | None = None,
        qdrant_factory: Callable[[TenantContext], Any] | None = None,
        publish: bool = False,
    ) -> None:
        self._repo = repository
        self._embedder = embedder  # may be None when indexing is skipped
        self._qdrant_factory = qdrant_factory
        self._publish = publish

    def ingest_fixture_dict(
        self,
        ctx: TenantContext,
        *,
        category: str,
        content: dict[str, Any],
        source_filename: str | None = None,
        verification_status: str = VerificationStatus.DRAFT.value,
        internal_only: bool = False,
        guest_visible: bool = True,
        source_type: str = SourceType.JSON_FIXTURE.value,
        dry_run: bool = False,
        actor_id: str | None = None,
    ) -> IngestionResult:
        # 2-3. validate + canonicalize
        Category.from_filename(category)  # raises on unsupported
        canonical = canonical_json(content)
        checksum = sha256_hex(canonical)

        # 4-5. idempotency: skip duplicate checksum
        if self._repo.checksum_exists(ctx.tenant_id, checksum):
            return IngestionResult(
                tenant_slug=ctx.tenant_slug,
                category=category,
                document_id=None,
                version=None,
                checksum=checksum,
                skipped=True,
                indexed=False,
                job_status=IngestionStatus.SKIPPED.value,
                chunks_created=0,
            )

        if dry_run:
            return IngestionResult(
                tenant_slug=ctx.tenant_slug,
                category=category,
                document_id=None,
                version=None,
                checksum=checksum,
                skipped=False,
                indexed=False,
                job_status=IngestionStatus.SKIPPED.value,
                chunks_created=0,
            )

        # 6-7. locate/create logical document + immutable version
        doc = self._repo.get_document(ctx.tenant_id, category)
        if doc is None:
            doc = self._repo.upsert_document(
                tenant_id=ctx.tenant_id,
                category=category,
                source_type=source_type,
                source_filename=source_filename,
            )
        version = self._repo.create_version(
            document_id=doc["id"],
            tenant_id=ctx.tenant_id,
            content=content,
            checksum=checksum,
            verification_status=verification_status,
            guest_visible=guest_visible,
            internal_only=internal_only,
        )
        # The newly created immutable version becomes the document's current one.
        self._repo.update_document_current_version(doc["id"], version["version"])
        # 8. record ingestion job, linked to the exact immutable version
        job = self._repo.create_job(
            tenant_id=ctx.tenant_id,
            source=source_filename or category,
            status=IngestionStatus.RUNNING.value,
            collection_name=ctx.qdrant_collection,
            checksum=checksum,
            document_version_id=version["id"],
        )

        indexable = (
            _is_indexable(verification_status, guest_visible, internal_only)
            and self._publish
        )
        published_at: str | None = None
        try:
            if indexable:
                if self._embedder is None or self._qdrant_factory is None:
                    raise IngestionError("indexing requested but embedder/store unavailable")
                # Publish in Supabase FIRST so state never lags behind Qdrant;
                # reverted below if indexing fails (never silently disagree).
                published_at = utc_now_iso()
                self._repo.update_version_state(version["id"], published_at=published_at)
                # 9-11. format, chunk, embed
                chunks = chunk_document(
                    category, content, source_filename=source_filename
                )
                vectors = self._embedder.embed([c.text for c in chunks])
                store = self._qdrant_factory(ctx)
                # 13. upsert with complete payload (incl. publication metadata)
                embedded = build_embedded_points(
                    ctx,
                    document_id=doc["id"],
                    version_row=version,
                    category=category,
                    checksum=checksum,
                    chunks=chunks,
                    vectors=vectors,
                    source_filename=source_filename,
                    published_at=published_at,
                )
                store.upsert_chunks(embedded)
                self._repo.update_job(job["id"], chunks_created=len(embedded))
                self._repo.update_job(
                    job["id"], status=IngestionStatus.COMPLETED.value, completed=True
                )
            else:
                # Not indexable (draft / unpublished / internal) — job done, no vectors.
                self._repo.update_job(
                    job["id"], status=IngestionStatus.COMPLETED.value, completed=True
                )
        except Exception as exc:  # noqa: BLE001 - fail closed, safe message
            if published_at is not None:
                # Roll the Supabase publication back so both stores agree
                # (unpublished + no vectors) instead of disagreeing silently.
                self._repo.update_version_state(version["id"], published_at=None)
            self._repo.update_job(
                job["id"],
                status=IngestionStatus.FAILED.value,
                error_message=_safe_message(exc),
                completed=True,
            )
            return IngestionResult(
                tenant_slug=ctx.tenant_slug,
                category=category,
                document_id=doc["id"],
                version=version["version"],
                checksum=checksum,
                skipped=False,
                indexed=False,
                job_status=IngestionStatus.FAILED.value,
                chunks_created=0,
                error=_safe_message(exc),
            )

        # 14-15. audit
        self._repo.audit(
            tenant_id=ctx.tenant_id,
            action="ingest_version",
            actor_type="system",
            actor_id=actor_id,
            document_id=doc["id"],
            document_version_id=version["id"],
            metadata={
                "category": category,
                "checksum": checksum,
                "indexed": indexable,
                "verification_status": verification_status,
            },
        )
        return IngestionResult(
            tenant_slug=ctx.tenant_slug,
            category=category,
            document_id=doc["id"],
            version=version["version"],
            checksum=checksum,
            skipped=False,
            indexed=indexable,
            job_status=IngestionStatus.COMPLETED.value,
            chunks_created=len(chunks) if indexable else 0,
        )

    def load_fixture_file(
        self, path: str, category: str, ctx: TenantContext, **kwargs: Any
    ) -> IngestionResult:
        if not path.endswith(".json"):
            raise IngestionError(f"only .json fixtures allowed: {path}")
        with open(path, encoding="utf-8") as fh:
            try:
                content = json.load(fh)
            except json.JSONDecodeError as exc:
                raise IngestionError(f"malformed JSON in {path}: {exc}") from exc
        source_filename = os.path.basename(path)
        return self.ingest_fixture_dict(
            ctx,
            category=category,
            content=content,
            source_filename=source_filename,
            **kwargs,
        )
