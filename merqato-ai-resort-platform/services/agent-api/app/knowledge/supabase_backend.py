"""Supabase-backed implementation of :class:`KnowledgeBackend`.

Writes go through the Supabase REST (PostgREST) API using the **service role**
key, which bypasses Row Level Security. The service role secret is read from the
environment and is never logged or returned. This backend is selected by the
seed CLI only when ``SUPABASE_URL`` and ``SUPABASE_SERVICE_ROLE_KEY`` are present;
unit tests continue to use the in-memory backend.

All writes are additive/upsert and never mutate existing version history in place
(versions are immutable; a new row is inserted per edit).
"""

from __future__ import annotations

from typing import Any

import requests

from app.knowledge.repository import KnowledgeBackend
from app.security.secrets import redact

# Tables (public schema).
_TENANTS = "tenants"
_DOCS = "tenant_knowledge_documents"
_VERSIONS = "tenant_knowledge_versions"
_JOBS = "knowledge_ingestion_jobs"
_AUDITS = "knowledge_audit_logs"


class SupabaseBackend(KnowledgeBackend):
    """Talk to a live Supabase project via PostgREST (service role)."""

    def __init__(self, base_url: str, service_role_key: str, *, timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/")
        self._key = service_role_key
        self._timeout = timeout

    # -- low-level helpers -------------------------------------------------
    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        h = {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        if prefer:
            h["Prefer"] = prefer
        return h

    def _table(self, name: str) -> str:
        return f"{self._base}/rest/v1/{name}"

    def _get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        try:
            r = requests.get(
                self._table(table),
                headers=self._headers(),
                params=params,
                timeout=self._timeout,
            )
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:  # fail closed, safe message
            raise RuntimeError(redact(str(exc))) from exc

    def _post(
        self,
        table: str,
        row: dict[str, Any],
        *,
        on_conflict: str | None = None,
    ) -> dict[str, Any]:
        prefer = "return=representation"
        if on_conflict:
            prefer = "resolution=merge-duplicates,return=representation"
            params = {"on_conflict": on_conflict}
        else:
            params = {}
        try:
            r = requests.post(
                self._table(table),
                headers=self._headers(prefer),
                params=params,
                json=row,
                timeout=self._timeout,
            )
            r.raise_for_status()
            data = r.json()
            return data[0] if isinstance(data, list) and data else row
        except requests.RequestException as exc:
            raise RuntimeError(redact(str(exc))) from exc

    def _patch(self, table: str, match: dict[str, str], values: dict[str, Any]) -> None:
        try:
            r = requests.patch(
                self._table(table),
                headers=self._headers("return=minimal"),
                params=match,
                json=values,
                timeout=self._timeout,
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(redact(str(exc))) from exc

    # -- KnowledgeBackend interface ---------------------------------------
    def fetch_tenant_by_slug(self, slug: str) -> dict[str, Any] | None:
        rows = self._get(_TENANTS, {"slug": f"eq.{slug}", "select": "*", "limit": "1"})
        return rows[0] if rows else None

    def upsert_tenant(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "slug": kwargs["slug"],
            "business_name": kwargs["business_name"],
            "business_type": kwargs["business_type"],
            "status": kwargs.get("status", "draft"),
        }
        if kwargs.get("primary_domain") is not None:
            row["primary_domain"] = kwargs["primary_domain"]
        if kwargs.get("widget_token_hash") is not None:
            row["widget_token_hash"] = kwargs["widget_token_hash"]
        return self._post(_TENANTS, row, on_conflict="slug")

    def fetch_document(self, tenant_id: str, category: str) -> dict[str, Any] | None:
        rows = self._get(
            _DOCS,
            {
                "tenant_id": f"eq.{tenant_id}",
                "category": f"eq.{category}",
                "select": "*",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def upsert_document(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "tenant_id": kwargs["tenant_id"],
            "category": kwargs["category"],
            "source_type": kwargs["source_type"],
            "source_filename": kwargs.get("source_filename"),
            "current_version": 0,
        }
        return self._post(_DOCS, row, on_conflict="tenant_id,category")

    def checksum_exists(self, tenant_id: str, checksum: str) -> bool:
        rows = self._get(
            _VERSIONS,
            {
                "tenant_id": f"eq.{tenant_id}",
                "checksum": f"eq.{checksum}",
                "select": "id",
                "limit": "1",
            },
        )
        return bool(rows)

    def insert_version(self, **kwargs: Any) -> dict[str, Any]:
        document_id = kwargs["document_id"]
        tenant_id = kwargs["tenant_id"]
        # Determine the next version number (immutable history: max+1).
        existing = self._get(
            _VERSIONS,
            {
                "document_id": f"eq.{document_id}",
                "select": "version",
                "order": "version.desc",
                "limit": "1",
            },
        )
        next_version = (existing[0]["version"] + 1) if existing else 1
        row = {
            "document_id": document_id,
            "tenant_id": tenant_id,
            "version": next_version,
            "content": kwargs["content"],
            "checksum": kwargs["checksum"],
            "verification_status": kwargs["verification_status"],
            "guest_visible": kwargs.get("guest_visible", True),
            "internal_only": kwargs.get("internal_only", False),
        }
        return self._post(_VERSIONS, row)

    def update_document_version(self, document_id: str, version: int) -> None:
        self._patch(
            _DOCS,
            {"id": f"eq.{document_id}"},
            {"current_version": version},
        )

    def insert_job(self, **kwargs: Any) -> dict[str, Any]:
        row = {
            "tenant_id": kwargs["tenant_id"],
            "source": kwargs["source"],
            "status": kwargs.get("status", "pending"),
            "collection_name": kwargs.get("collection_name"),
            "checksum": kwargs.get("checksum"),
        }
        return self._post(_JOBS, row)

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        values: dict[str, Any] = {}
        if kwargs.get("status") is not None:
            values["status"] = kwargs["status"]
        if kwargs.get("chunks_created") is not None:
            values["chunks_created"] = kwargs["chunks_created"]
        if kwargs.get("error_message") is not None:
            values["error_message"] = kwargs["error_message"]
        if kwargs.get("completed"):
            values["completed_at"] = "now()"
        if values:
            self._patch(_JOBS, {"id": f"eq.{job_id}"}, values)

    def insert_audit(self, **kwargs: Any) -> None:
        row = {
            "tenant_id": kwargs["tenant_id"],
            "action": kwargs["action"],
            "actor_type": kwargs["actor_type"],
            "actor_id": kwargs.get("actor_id"),
            "document_id": kwargs.get("document_id"),
            "document_version_id": kwargs.get("document_version_id"),
            "metadata": kwargs.get("metadata", {}),
        }
        self._post(_AUDITS, row)
