"""Admin knowledge lifecycle: draft → verify → publish → unpublish/archive.

Every state change writes an audit record. Publication keeps Supabase and
Qdrant in agreement:

  * publish: set ``published_at`` in Supabase first, then (re)index into the
    tenant's Qdrant collection with publication metadata in every payload. If
    indexing fails, the Supabase publication is rolled back — the two stores
    never disagree silently.
  * unpublish/archive: clear ``published_at`` first, then remove the
    document's vectors from Qdrant.

Only one published version per document exists at a time; publishing a new
version unpublishes its predecessors in the same operation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.knowledge.chunker import chunk_document
from app.knowledge.formatter import canonical_json
from app.knowledge.ingestion_service import build_embedded_points
from app.knowledge.models import (
    Category,
    IngestionStatus,
    SourceType,
    VerificationStatus,
    utc_now_iso,
)
from app.knowledge.repository import KnowledgeRepository, sha256_hex
from app.security.secrets import redact
from app.services.tenant_resolver import TenantContext


class PublishingError(Exception):
    """Admin knowledge lifecycle failure with a safe, redacted message."""


class PublishStateError(PublishingError):
    """The requested transition is not allowed from the version's state."""


class DuplicateContentError(PublishingError):
    """The submitted content is identical to an existing version."""


class PublishingService:
    """Tenant-scoped knowledge lifecycle operations for the Admin workflow."""

    def __init__(
        self,
        repository: KnowledgeRepository,
        *,
        embedder: Any | None = None,
        qdrant_factory: Callable[[TenantContext], Any] | None = None,
    ) -> None:
        self._repo = repository
        self._embedder = embedder
        self._qdrant_factory = qdrant_factory

    # -- reads ---------------------------------------------------------------
    def list_categories(self, ctx: TenantContext) -> list[dict[str, Any]]:
        """All 10 categories with document/current-version state (if any)."""
        docs = {d["category"]: d for d in self._repo.list_documents(ctx.tenant_id)}
        out: list[dict[str, Any]] = []
        for cat in Category:
            doc = docs.get(cat.value)
            entry: dict[str, Any] = {
                "category": cat.value,
                "document_id": doc["id"] if doc else None,
                "current_version": doc["current_version"] if doc else 0,
                "verification_status": None,
                "published": False,
                "published_at": None,
            }
            if doc:
                current = self._current_version_row(doc)
                if current:
                    entry["verification_status"] = current["verification_status"]
                    entry["published"] = bool(current.get("published_at"))
                    entry["published_at"] = current.get("published_at")
            out.append(entry)
        return out

    def get_current(self, ctx: TenantContext, category: str) -> dict[str, Any] | None:
        """The document and its current version row for a category."""
        Category.from_filename(category)
        doc = self._repo.get_document(ctx.tenant_id, category)
        if doc is None:
            return None
        current = self._current_version_row(doc)
        return {"document": doc, "version": current}

    def list_versions(self, ctx: TenantContext, category: str) -> list[dict[str, Any]]:
        Category.from_filename(category)
        doc = self._repo.get_document(ctx.tenant_id, category)
        if doc is None:
            return []
        return self._repo.list_versions(doc["id"])

    def list_audits(
        self, ctx: TenantContext, category: str | None = None, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        document_id = None
        if category is not None:
            Category.from_filename(category)
            doc = self._repo.get_document(ctx.tenant_id, category)
            if doc is None:
                return []
            document_id = doc["id"]
        return self._repo.list_audits(
            ctx.tenant_id, document_id=document_id, limit=limit
        )

    def list_jobs(
        self, ctx: TenantContext, *, document_version_id: str | None = None
    ) -> list[dict[str, Any]]:
        return self._repo.list_jobs(
            ctx.tenant_id, document_version_id=document_version_id
        )

    # -- writes ----------------------------------------------------------------
    def create_draft(
        self,
        ctx: TenantContext,
        *,
        category: str,
        content: dict[str, Any],
        guest_visible: bool = True,
        internal_only: bool = False,
        source_type: str = SourceType.DASHBOARD_FORM.value,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a NEW immutable draft version (history is never edited)."""
        Category.from_filename(category)
        checksum = sha256_hex(canonical_json(content))
        if self._repo.checksum_exists(ctx.tenant_id, checksum):
            raise DuplicateContentError(
                "identical content already exists as a version for this tenant"
            )
        doc = self._repo.get_document(ctx.tenant_id, category)
        if doc is None:
            doc = self._repo.upsert_document(
                tenant_id=ctx.tenant_id,
                category=category,
                source_type=source_type,
                source_filename=None,
            )
        version = self._repo.create_version(
            document_id=doc["id"],
            tenant_id=ctx.tenant_id,
            content=content,
            checksum=checksum,
            verification_status=VerificationStatus.DRAFT.value,
            guest_visible=guest_visible,
            internal_only=internal_only,
        )
        self._repo.update_document_current_version(doc["id"], version["version"])
        self._audit(
            ctx, "create_draft", actor_id, doc["id"], version["id"],
            {"category": category, "version": version["version"], "checksum": checksum},
        )
        return version

    def verify(
        self, ctx: TenantContext, version_id: str, *, actor_id: str | None = None
    ) -> dict[str, Any]:
        """Mark a draft version verified (human approval, never automatic)."""
        version = self._require_version(ctx, version_id)
        if version["verification_status"] != VerificationStatus.DRAFT.value:
            raise PublishStateError(
                f"only draft versions can be verified "
                f"(status={version['verification_status']!r})"
            )
        self._repo.update_version_state(
            version_id,
            verification_status=VerificationStatus.VERIFIED.value,
            approved_at=utc_now_iso(),
        )
        self._audit(
            ctx, "verify_version", actor_id, version["document_id"], version_id,
            {"version": version["version"]},
        )
        updated = self._repo.get_version(version_id)
        assert updated is not None
        return updated

    def publish(
        self, ctx: TenantContext, version_id: str, *, actor_id: str | None = None
    ) -> dict[str, Any]:
        """Publish a verified version: Supabase publication + Qdrant indexing."""
        version = self._require_version(ctx, version_id)
        if version["verification_status"] != VerificationStatus.VERIFIED.value:
            raise PublishStateError(
                f"only verified versions can be published "
                f"(status={version['verification_status']!r})"
            )
        if not version.get("guest_visible", False) or version.get("internal_only", True):
            raise PublishStateError(
                "only guest-visible, non-internal versions can be published"
            )
        if self._embedder is None or self._qdrant_factory is None:
            raise PublishingError(
                "publishing requires embeddings and Qdrant to be configured"
            )
        document_id = version["document_id"]
        category = self._category_of(ctx, document_id)

        # Single published version per document: retire the predecessors.
        previously_published = [
            v
            for v in self._repo.list_versions(document_id)
            if v.get("published_at") and v["id"] != version_id
        ]

        published_at = utc_now_iso()
        # Supabase first; rolled back below if indexing fails.
        self._repo.update_version_state(version_id, published_at=published_at)
        for old in previously_published:
            self._repo.update_version_state(old["id"], published_at=None)

        job = self._repo.create_job(
            tenant_id=ctx.tenant_id,
            source=f"publish:{category}",
            status=IngestionStatus.RUNNING.value,
            collection_name=ctx.qdrant_collection,
            checksum=version["checksum"],
            document_version_id=version_id,
        )
        try:
            chunks = chunk_document(category, version["content"], source_filename=None)
            vectors = self._embedder.embed([c.text for c in chunks])
            store = self._qdrant_factory(ctx)
            points = build_embedded_points(
                ctx,
                document_id=document_id,
                version_row=version,
                category=category,
                checksum=version["checksum"],
                chunks=chunks,
                vectors=vectors,
                source_filename=None,
                published_at=published_at,
            )
            # Replace any previously indexed vectors for this document.
            store.delete_document_vectors(document_id)
            store.upsert_chunks(points)
        except Exception as exc:  # noqa: BLE001 - fail closed, stores must agree
            self._repo.update_version_state(version_id, published_at=None)
            for old in previously_published:
                self._repo.update_version_state(
                    old["id"], published_at=old["published_at"]
                )
            self._repo.update_job(
                job["id"],
                status=IngestionStatus.FAILED.value,
                error_message=redact(str(exc))[:500],
                completed=True,
            )
            self._audit(
                ctx, "publish_failed", actor_id, document_id, version_id,
                {"version": version["version"], "error": redact(str(exc))[:200]},
            )
            raise PublishingError(f"publish failed: {redact(str(exc))[:200]}") from exc

        self._repo.update_job(
            job["id"],
            status=IngestionStatus.COMPLETED.value,
            chunks_created=len(points),
            completed=True,
        )
        self._audit(
            ctx, "publish_version", actor_id, document_id, version_id,
            {
                "version": version["version"],
                "published_at": published_at,
                "chunks": len(points),
                "unpublished_predecessors": [v["id"] for v in previously_published],
            },
        )
        updated = self._repo.get_version(version_id)
        assert updated is not None
        return updated

    def unpublish(
        self,
        ctx: TenantContext,
        version_id: str,
        *,
        archive: bool = False,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        """Withdraw a published version from guests (optionally archive it).

        Supabase is updated first, then the document's vectors are removed
        from Qdrant. Vector deletion failures surface loudly (the content is
        already unpublished in Supabase, which fails safe for guests once
        retrieval filters on the published payload).
        """
        version = self._require_version(ctx, version_id)
        was_published = bool(version.get("published_at"))
        state: dict[str, Any] = {"published_at": None}
        if archive:
            state["verification_status"] = VerificationStatus.ARCHIVED.value
        self._repo.update_version_state(version_id, **state)

        if was_published:
            if self._qdrant_factory is None:
                raise PublishingError(
                    "unpublishing indexed content requires Qdrant to be configured"
                )
            store = self._qdrant_factory(ctx)
            store.delete_document_vectors(version["document_id"])

        self._audit(
            ctx,
            "archive_version" if archive else "unpublish_version",
            actor_id,
            version["document_id"],
            version_id,
            {"version": version["version"], "was_published": was_published},
        )
        updated = self._repo.get_version(version_id)
        assert updated is not None
        return updated

    # -- helpers ---------------------------------------------------------------
    def _current_version_row(self, doc: dict[str, Any]) -> dict[str, Any] | None:
        versions = self._repo.list_versions(doc["id"])
        if not versions:
            return None
        for v in versions:
            if v["version"] == doc.get("current_version"):
                return v
        return versions[0]  # newest first

    def _require_version(self, ctx: TenantContext, version_id: str) -> dict[str, Any]:
        version = self._repo.get_version(version_id)
        if version is None or str(version.get("tenant_id")) != str(ctx.tenant_id):
            # One error for both cases: never confirm other tenants' version ids.
            raise PublishStateError("version not found for this tenant")
        return version

    def _category_of(self, ctx: TenantContext, document_id: str) -> str:
        for doc in self._repo.list_documents(ctx.tenant_id):
            if doc["id"] == document_id:
                return str(doc["category"])
        raise PublishStateError("document not found for this tenant")

    def _audit(
        self,
        ctx: TenantContext,
        action: str,
        actor_id: str | None,
        document_id: str | None,
        version_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._repo.audit(
            tenant_id=ctx.tenant_id,
            action=action,
            actor_type="admin",
            actor_id=actor_id,
            document_id=document_id,
            document_version_id=version_id,
            metadata=metadata,
        )
