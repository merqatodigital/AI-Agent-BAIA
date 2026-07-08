from __future__ import annotations

import hashlib
from typing import Any

from app.knowledge.models import (
    IngestionStatus,
    new_uuid,
)


def sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class KnowledgeRepository:
    """Owns all Supabase reads/writes for the multi-tenant knowledge model.

    A single backend callable surface is injected so tests can use an
    in-memory fake without a live Supabase connection. When no backend is
    supplied, a process-wide default in-memory backend is shared so that any
    KnowledgeRepository() instance observes tenant/seed state consistently
    (e.g. the concierge service resolves a tenant seeded elsewhere). The
    production backend (Supabase service-role client) is wired in later; this
    class never performs CrewAI execution and never logs or returns secrets.
    """

    def __init__(
        self,
        backend: KnowledgeBackend | None = None,
    ) -> None:
        self._backend = backend or _default_backend()

    # --- tenant ----------------------------------------------------------
    def get_tenant_by_slug(self, slug: str) -> dict[str, Any] | None:
        return self._backend.fetch_tenant_by_slug(slug)

    def upsert_tenant(
        self,
        *,
        slug: str,
        business_name: str,
        business_type: str,
        status: str = "draft",
        primary_domain: str | None = None,
        widget_token_hash: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.upsert_tenant(
            slug=slug,
            business_name=business_name,
            business_type=business_type,
            status=status,
            primary_domain=primary_domain,
            widget_token_hash=widget_token_hash,
        )

    # --- logical document ------------------------------------------------
    def get_document(self, tenant_id: str, category: str) -> dict[str, Any] | None:
        return self._backend.fetch_document(tenant_id, category)

    def upsert_document(
        self,
        *,
        tenant_id: str,
        category: str,
        source_type: str,
        source_filename: str | None,
    ) -> dict[str, Any]:
        return self._backend.upsert_document(
            tenant_id=tenant_id,
            category=category,
            source_type=source_type,
            source_filename=source_filename,
        )

    # --- immutable version -----------------------------------------------
    def checksum_exists(self, tenant_id: str, checksum: str) -> bool:
        return self._backend.checksum_exists(tenant_id, checksum)

    def create_version(
        self,
        *,
        document_id: str,
        tenant_id: str,
        content: dict[str, Any],
        checksum: str,
        verification_status: str,
        guest_visible: bool = True,
        internal_only: bool = False,
    ) -> dict[str, Any]:
        return self._backend.insert_version(
            document_id=document_id,
            tenant_id=tenant_id,
            content=content,
            checksum=checksum,
            verification_status=verification_status,
            guest_visible=guest_visible,
            internal_only=internal_only,
        )

    def update_document_current_version(
        self, document_id: str, version: int
    ) -> None:
        self._backend.update_document_version(document_id, version)

    # --- ingestion job ---------------------------------------------------
    def create_job(
        self,
        *,
        tenant_id: str,
        source: str,
        status: str = IngestionStatus.PENDING.value,
        collection_name: str | None = None,
        checksum: str | None = None,
        document_version_id: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.insert_job(
            tenant_id=tenant_id,
            source=source,
            status=status,
            collection_name=collection_name,
            checksum=checksum,
            document_version_id=document_version_id,
        )

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        chunks_created: int | None = None,
        error_message: str | None = None,
        completed: bool = False,
    ) -> None:
        self._backend.update_job(
            job_id,
            status=status,
            chunks_created=chunks_created,
            error_message=error_message,
            completed=completed,
        )

    # --- audit -----------------------------------------------------------
    def audit(
        self,
        *,
        tenant_id: str,
        action: str,
        actor_type: str,
        actor_id: str | None = None,
        document_id: str | None = None,
        document_version_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._backend.insert_audit(
            tenant_id=tenant_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            document_id=document_id,
            document_version_id=document_version_id,
            metadata=metadata or {},
        )


class KnowledgeBackend:
    """Interface the repository delegates to (Supabase in prod, fake in tests)."""

    def fetch_tenant_by_slug(self, slug: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def upsert_tenant(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def fetch_document(self, tenant_id: str, category: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def upsert_document(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def checksum_exists(self, tenant_id: str, checksum: str) -> bool:
        raise NotImplementedError

    def insert_version(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update_document_version(self, document_id: str, version: int) -> None:
        raise NotImplementedError

    def insert_job(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        raise NotImplementedError

    def insert_audit(self, **kwargs: Any) -> None:
        raise NotImplementedError


class _InMemoryBackend(KnowledgeBackend):
    """Default backend used when none is supplied (no live Supabase)."""

    def __init__(self) -> None:
        self.tenants: dict[str, dict[str, Any]] = {}
        self.tenant_by_slug: dict[str, str] = {}
        self.documents: list[dict[str, Any]] = []
        self.versions: list[dict[str, Any]] = []
        self.jobs: list[dict[str, Any]] = []
        self.audits: list[dict[str, Any]] = []

    def fetch_tenant_by_slug(self, slug: str) -> dict[str, Any] | None:
        tid = self.tenant_by_slug.get(slug)
        return self.tenants.get(tid) if tid else None

    def upsert_tenant(self, **kwargs: Any) -> dict[str, Any]:
        slug = kwargs["slug"]
        existing = self.tenant_by_slug.get(slug)
        if existing:
            row = self.tenants[existing]
            row.update(
                business_name=kwargs["business_name"],
                business_type=kwargs["business_type"],
                status=kwargs.get("status", row["status"]),
                primary_domain=kwargs.get("primary_domain"),
                widget_token_hash=kwargs.get("widget_token_hash"),
            )
            return row
        row = {
            "id": new_uuid(),
            "slug": slug,
            "business_name": kwargs["business_name"],
            "business_type": kwargs["business_type"],
            "status": kwargs.get("status", "draft"),
            "primary_domain": kwargs.get("primary_domain"),
            "widget_token_hash": kwargs.get("widget_token_hash"),
        }
        self.tenants[row["id"]] = row
        self.tenant_by_slug[slug] = row["id"]
        return row

    def fetch_document(self, tenant_id: str, category: str) -> dict[str, Any] | None:
        for d in self.documents:
            if d["tenant_id"] == tenant_id and d["category"] == category:
                return d
        return None

    def upsert_document(self, **kwargs: Any) -> dict[str, Any]:
        tenant_id = kwargs["tenant_id"]
        category = kwargs["category"]
        existing = self.fetch_document(tenant_id, category)
        if existing:
            existing.update(
                source_type=kwargs["source_type"],
                source_filename=kwargs.get("source_filename"),
            )
            return existing
        row = {
            "id": new_uuid(),
            "tenant_id": tenant_id,
            "category": category,
            "source_type": kwargs["source_type"],
            "source_filename": kwargs.get("source_filename"),
            "current_version": 0,
        }
        self.documents.append(row)
        return row

    def checksum_exists(self, tenant_id: str, checksum: str) -> bool:
        return any(
            v["tenant_id"] == tenant_id and v["checksum"] == checksum
            for v in self.versions
        )

    def insert_version(self, **kwargs: Any) -> dict[str, Any]:
        # Determine next version number for this document (max+1, immutable).
        numbers = [
            v["version"] for v in self.versions if v["document_id"] == kwargs["document_id"]
        ]
        version = (max(numbers) + 1) if numbers else 1
        row = {
            "id": new_uuid(),
            "document_id": kwargs["document_id"],
            "tenant_id": kwargs["tenant_id"],
            "version": version,
            "content": kwargs["content"],
            "checksum": kwargs["checksum"],
            "verification_status": kwargs["verification_status"],
            "guest_visible": kwargs.get("guest_visible", True),
            "internal_only": kwargs.get("internal_only", False),
            "published_at": None,
        }
        self.versions.append(row)
        return row

    def update_document_version(self, document_id: str, version: int) -> None:
        for d in self.documents:
            if d["id"] == document_id:
                d["current_version"] = version

    def insert_job(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "id": new_uuid(),
            "tenant_id": kwargs["tenant_id"],
            "document_version_id": kwargs.get("document_version_id"),
            "status": kwargs["status"],
            "source": kwargs["source"],
            "collection_name": kwargs.get("collection_name"),
            "chunks_created": 0,
            "checksum": kwargs.get("checksum"),
            "error_message": None,
        }
        self.jobs.append(row)
        return row

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        for j in self.jobs:
            if j["id"] == job_id:
                if kwargs.get("status") is not None:
                    j["status"] = kwargs["status"]
                if kwargs.get("chunks_created") is not None:
                    j["chunks_created"] = kwargs["chunks_created"]
                if kwargs.get("error_message") is not None:
                    j["error_message"] = kwargs["error_message"]
                if kwargs.get("completed"):
                    j["completed_at"] = "now"

    def insert_audit(self, **kwargs: Any) -> None:
        self.audits.append(
            {
                "id": new_uuid(),
                "tenant_id": kwargs["tenant_id"],
                "action": kwargs["action"],
                "actor_type": kwargs["actor_type"],
                "actor_id": kwargs.get("actor_id"),
                "document_id": kwargs.get("document_id"),
                "document_version_id": kwargs.get("document_version_id"),
                "metadata": kwargs.get("metadata", {}),
            }
        )


# Process-wide default in-memory backend. Shared by any KnowledgeRepository()
# created without an explicit backend, so tenant seeds are visible across
# instances (e.g. concierge service resolving a seeded tenant). Reset in tests
# that need isolation via reset_default_backend().
_default_memory: KnowledgeBackend | None = None


def _default_backend() -> KnowledgeBackend:
    """Select the runtime backend.

    Live Supabase (service role) whenever SUPABASE_URL and
    SUPABASE_SERVICE_ROLE_KEY are configured; the shared in-memory backend
    otherwise (tests / zero-config local runs).
    """
    from app.config import get_settings  # local import: avoid settings at import time

    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        # Local import: supabase_backend imports from this module.
        from app.knowledge.supabase_backend import SupabaseBackend

        return SupabaseBackend(
            settings.supabase_url, settings.supabase_service_role_key
        )
    global _default_memory
    if _default_memory is None:
        _default_memory = _InMemoryBackend()
    return _default_memory


def reset_default_backend() -> None:
    """Discard and recreate the shared default in-memory backend (test helper)."""
    global _default_memory
    _default_memory = _InMemoryBackend()
