"""SupabaseBackend correctness under conflict/concurrency (no live Supabase).

The REST transport (_get/_post/_patch) is replaced by an in-memory PostgREST
stand-in that enforces the same unique constraints as the migration, so the
version-race retry, non-destructive document upsert, and timestamp handling
are exercised exactly as PostgREST would see them.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from app.knowledge.supabase_backend import SupabaseBackend, VersionConflictError


class FakeRestBackend(SupabaseBackend):
    """SupabaseBackend with the REST layer swapped for in-memory tables."""

    def __init__(self) -> None:
        super().__init__("https://fake.supabase.co", "fake-service-role-key")
        self.tables: dict[str, list[dict[str, Any]]] = {
            "tenants": [],
            "tenant_knowledge_documents": [],
            "tenant_knowledge_versions": [],
            "knowledge_ingestion_jobs": [],
            "knowledge_audit_logs": [],
        }
        self._id = 0
        # Optional hook invoked before each POST (simulates a racing writer).
        self.before_post: Any = None

    def _new_id(self) -> str:
        self._id += 1
        return f"id-{self._id}"

    @staticmethod
    def _matches(row: dict[str, Any], params: dict[str, str]) -> bool:
        for key, expr in params.items():
            if key in ("select", "limit", "order", "on_conflict", "offset"):
                continue
            m = re.fullmatch(r"eq\.(.*)", expr)
            if m and str(row.get(key)) != m.group(1):
                return False
        return True

    def _get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        rows = [r for r in self.tables[table] if self._matches(r, params)]
        order = params.get("order")
        if order:
            col, _, direction = order.partition(".")
            rows.sort(key=lambda r: r.get(col) or 0, reverse=direction == "desc")
        limit = params.get("limit")
        if limit:
            rows = rows[: int(limit)]
        return [dict(r) for r in rows]

    def _post(
        self, table: str, row: dict[str, Any], *, on_conflict: str | None = None
    ) -> dict[str, Any]:
        if self.before_post is not None:
            hook, self.before_post = self.before_post, None
            hook(table, row)
        if table == "tenant_knowledge_versions":
            # unique(document_id, version) — plain insert conflicts like the DB.
            for r in self.tables[table]:
                if (
                    r["document_id"] == row["document_id"]
                    and r["version"] == row["version"]
                ):
                    raise RuntimeError("409 Client Error: Conflict (duplicate key)")
        if on_conflict:
            keys = on_conflict.split(",")
            for r in self.tables[table]:
                if all(r.get(k) == row.get(k) for k in keys):
                    # merge-duplicates: update only the supplied columns.
                    r.update(row)
                    return dict(r)
        stored = dict(row)
        stored.setdefault("id", self._new_id())
        if table == "tenant_knowledge_documents":
            stored.setdefault("current_version", 0)  # DB column default
        if table == "tenant_knowledge_versions":
            stored.setdefault("published_at", None)
        self.tables[table].append(stored)
        return dict(stored)

    def _patch(self, table: str, match: dict[str, str], values: dict[str, Any]) -> None:
        for r in self.tables[table]:
            if self._matches(r, match):
                r.update(values)


@pytest.fixture
def backend() -> FakeRestBackend:
    b = FakeRestBackend()
    b.upsert_tenant(slug="baia-resort", business_name="BAIA", business_type="resort")
    return b


def _tenant_id(backend: FakeRestBackend) -> str:
    row = backend.fetch_tenant_by_slug("baia-resort")
    assert row is not None
    return row["id"]


def test_document_upsert_preserves_current_version(backend: FakeRestBackend):
    tid = _tenant_id(backend)
    doc = backend.upsert_document(
        tenant_id=tid, category="faq", source_type="json_fixture", source_filename="faq.json"
    )
    backend.update_document_version(doc["id"], 3)
    again = backend.upsert_document(
        tenant_id=tid, category="faq", source_type="dashboard_form", source_filename=None
    )
    assert again["id"] == doc["id"]
    assert again["current_version"] == 3  # NOT reset to 0
    assert again["source_type"] == "dashboard_form"


def test_versions_are_immutable_and_sequential(backend: FakeRestBackend):
    tid = _tenant_id(backend)
    doc = backend.upsert_document(
        tenant_id=tid, category="faq", source_type="json_fixture", source_filename=None
    )
    v1 = backend.insert_version(
        document_id=doc["id"], tenant_id=tid, content={"a": 1},
        checksum="c1", verification_status="draft",
    )
    v2 = backend.insert_version(
        document_id=doc["id"], tenant_id=tid, content={"a": 2},
        checksum="c2", verification_status="draft",
    )
    assert (v1["version"], v2["version"]) == (1, 2)
    stored = backend.tables["tenant_knowledge_versions"]
    assert len(stored) == 2
    assert stored[0]["content"] == {"a": 1}  # v1 untouched by v2 insert


def test_version_race_retries_and_wins(backend: FakeRestBackend):
    tid = _tenant_id(backend)
    doc = backend.upsert_document(
        tenant_id=tid, category="faq", source_type="json_fixture", source_filename=None
    )

    def racing_writer(table: str, row: dict[str, Any]) -> None:
        if table == "tenant_knowledge_versions":
            backend.tables[table].append(
                {
                    "id": backend._new_id(),
                    "document_id": row["document_id"],
                    "tenant_id": tid,
                    "version": row["version"],  # steals the number first
                    "content": {"racer": True},
                    "checksum": "racer",
                    "verification_status": "draft",
                    "guest_visible": True,
                    "internal_only": False,
                    "published_at": None,
                }
            )

    backend.before_post = racing_writer
    v = backend.insert_version(
        document_id=doc["id"], tenant_id=tid, content={"mine": True},
        checksum="mine", verification_status="draft",
    )
    assert v["version"] == 2  # retried past the stolen number
    assert len(backend.tables["tenant_knowledge_versions"]) == 2


def test_version_race_exhaustion_fails_loudly(backend: FakeRestBackend):
    tid = _tenant_id(backend)
    doc = backend.upsert_document(
        tenant_id=tid, category="faq", source_type="json_fixture", source_filename=None
    )
    original_post = backend._post

    def always_conflict(table: str, row: dict[str, Any], **kw: Any) -> dict[str, Any]:
        if table == "tenant_knowledge_versions":
            raise RuntimeError("409 Client Error: Conflict (duplicate key)")
        return original_post(table, row, **kw)

    backend._post = always_conflict  # type: ignore[method-assign]
    with pytest.raises(VersionConflictError):
        backend.insert_version(
            document_id=doc["id"], tenant_id=tid, content={},
            checksum="x", verification_status="draft",
        )


def test_job_links_version_and_records_real_timestamps(backend: FakeRestBackend):
    tid = _tenant_id(backend)
    job = backend.insert_job(
        tenant_id=tid,
        source="faq.json",
        status="running",
        collection_name="merqato_tenant_baia_resort",
        checksum="c1",
        document_version_id="version-123",
    )
    assert job["document_version_id"] == "version-123"
    assert "now()" not in str(job.get("started_at"))
    backend.update_job(job["id"], status="completed", completed=True)
    stored = backend.tables["knowledge_ingestion_jobs"][0]
    assert stored["status"] == "completed"
    completed_at = stored["completed_at"]
    assert completed_at != "now()" and "T" in completed_at  # real ISO timestamp
