"""Admin knowledge lifecycle: draft → verify → publish → unpublish/archive.

Covers the Supabase/Qdrant consistency contract: publication metadata is
present in indexed payloads, retrieval filters exclude anything unpublished,
and failed indexing rolls the Supabase publication back.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.publishing_service import (
    DuplicateContentError,
    PublishingError,
    PublishingService,
    PublishStateError,
)
from app.knowledge.repository import KnowledgeRepository, _InMemoryBackend
from app.services.tenant_resolver import make_tenant_context
from tests.qdrant_fakes import FilterAwareVectorClient, make_store

TENANT_ID = "00000000-0000-0000-0000-0000000000aa"
SLUG = "baia-resort"


@pytest.fixture
def repo() -> KnowledgeRepository:
    return KnowledgeRepository(backend=_InMemoryBackend())


@pytest.fixture
def vector_client() -> FilterAwareVectorClient:
    return FilterAwareVectorClient(dimension=8)


@pytest.fixture
def service(repo, vector_client) -> PublishingService:
    return PublishingService(
        repo,
        embedder=FakeEmbeddingProvider(dimension=8),
        qdrant_factory=lambda ctx: make_store(
            ctx.tenant_id, ctx.tenant_slug, client=vector_client
        ),
    )


@pytest.fixture
def ctx():
    return make_tenant_context(TENANT_ID, SLUG, "active")


def _audit_actions(repo: KnowledgeRepository) -> list[str]:
    return [a["action"] for a in repo.list_audits(TENANT_ID)]


CONTENT_V1 = {"summary": "Breakfast is served 7-10am", "details": ["Filipino", "Continental"]}
CONTENT_V2 = {"summary": "Breakfast is served 6:30-10am", "details": ["Filipino"]}


def test_create_draft_is_immutable_and_audited(service, repo, ctx, vector_client):
    v1 = service.create_draft(ctx, category="food_breakfast", content=CONTENT_V1)
    assert v1["version"] == 1
    assert v1["verification_status"] == "draft"
    assert v1["published_at"] is None

    v2 = service.create_draft(ctx, category="food_breakfast", content=CONTENT_V2)
    assert v2["version"] == 2
    # v1 history row untouched
    stored_v1 = repo.get_version(v1["id"])
    assert stored_v1 is not None and stored_v1["content"] == CONTENT_V1
    # document points at the newest version
    doc = repo.get_document(ctx.tenant_id, "food_breakfast")
    assert doc is not None and doc["current_version"] == 2
    # drafts create NO vectors
    assert vector_client.all_points("merqato_tenant_baia_resort") == []
    assert _audit_actions(repo).count("create_draft") == 2


def test_duplicate_draft_content_is_rejected(service, ctx):
    service.create_draft(ctx, category="faq", content=CONTENT_V1)
    with pytest.raises(DuplicateContentError):
        service.create_draft(ctx, category="faq", content=dict(CONTENT_V1))


def test_verify_requires_draft_and_audits(service, repo, ctx):
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    verified = service.verify(ctx, v["id"])
    assert verified["verification_status"] == "verified"
    assert verified["approved_at"] is not None
    assert "verify_version" in _audit_actions(repo)
    with pytest.raises(PublishStateError):
        service.verify(ctx, v["id"])  # already verified


def test_publish_requires_verified(service, ctx):
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    with pytest.raises(PublishStateError):
        service.publish(ctx, v["id"])


def test_publish_indexes_with_publication_metadata(service, repo, ctx, vector_client):
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v["id"])
    published = service.publish(ctx, v["id"])
    assert published["published_at"] is not None

    points = vector_client.all_points("merqato_tenant_baia_resort")
    assert points, "publish must index vectors"
    for p in points:
        payload = p["payload"]
        assert payload["published"] is True
        assert payload["published_at"] == published["published_at"]
        assert payload["verification_status"] == "verified"
        assert payload["document_version_id"] == v["id"]
        assert payload["tenant_id"] == TENANT_ID

    jobs = repo.list_jobs(TENANT_ID, document_version_id=v["id"])
    assert jobs and jobs[0]["status"] == "completed"
    assert jobs[0]["chunks_created"] == len(points)
    assert "publish_version" in _audit_actions(repo)


def test_publishing_new_version_retires_predecessor(service, repo, ctx, vector_client):
    v1 = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v1["id"])
    service.publish(ctx, v1["id"])

    v2 = service.create_draft(ctx, category="faq", content=CONTENT_V2)
    service.verify(ctx, v2["id"])
    service.publish(ctx, v2["id"])

    old = repo.get_version(v1["id"])
    assert old is not None and old["published_at"] is None  # predecessor retired
    points = vector_client.all_points("merqato_tenant_baia_resort")
    assert points
    assert {p["payload"]["document_version_id"] for p in points} == {v2["id"]}


def test_failed_indexing_rolls_back_supabase_publication(repo, ctx, vector_client):
    class ExplodingEmbedder(FakeEmbeddingProvider):
        def embed(self, texts):
            raise RuntimeError("qdrant/embedding backend down")

    service = PublishingService(
        repo,
        embedder=ExplodingEmbedder(dimension=8),
        qdrant_factory=lambda c: make_store(c.tenant_id, c.tenant_slug, client=vector_client),
    )
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v["id"])
    with pytest.raises(PublishingError):
        service.publish(ctx, v["id"])

    stored = repo.get_version(v["id"])
    assert stored is not None and stored["published_at"] is None  # rolled back
    assert vector_client.all_points("merqato_tenant_baia_resort") == []
    jobs = repo.list_jobs(TENANT_ID, document_version_id=v["id"])
    assert jobs and jobs[0]["status"] == "failed"
    assert "publish_failed" in _audit_actions(repo)


def test_unpublish_clears_supabase_and_qdrant(service, repo, ctx, vector_client):
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v["id"])
    service.publish(ctx, v["id"])

    updated = service.unpublish(ctx, v["id"])
    assert updated["published_at"] is None
    assert updated["verification_status"] == "verified"  # not archived
    assert vector_client.all_points("merqato_tenant_baia_resort") == []
    assert "unpublish_version" in _audit_actions(repo)


def test_archive_marks_version_archived(service, repo, ctx, vector_client):
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v["id"])
    service.publish(ctx, v["id"])
    updated = service.unpublish(ctx, v["id"], archive=True)
    assert updated["verification_status"] == "archived"
    assert "archive_version" in _audit_actions(repo)


def test_versions_of_other_tenants_are_invisible(service, ctx):
    other_ctx = make_tenant_context(
        "00000000-0000-0000-0000-0000000000bb", "other-resort", "active"
    )
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    with pytest.raises(PublishStateError):
        service.verify(other_ctx, v["id"])


def test_search_never_returns_unpublished_content(service, ctx, vector_client):
    """Defense-in-depth: even vectors indexed WITHOUT publication metadata
    (e.g. by an older indexer) are invisible to the guest search filter."""
    store = make_store(TENANT_ID, SLUG, client=vector_client)
    store.ensure_collection()
    vector_client.upsert(
        "merqato_tenant_baia_resort",
        [
            {
                "id": "rogue-1",
                "vector": [0.1] * 8,
                "payload": {
                    "tenant_id": TENANT_ID,
                    "verification_status": "draft",
                    "guest_visible": True,
                    "internal_only": False,
                    "text": "unverified rumor",
                },
            },
            {
                "id": "rogue-2",
                "vector": [0.1] * 8,
                "payload": {
                    "tenant_id": TENANT_ID,
                    "verification_status": "verified",
                    # no `published` flag at all
                    "guest_visible": True,
                    "internal_only": False,
                    "text": "verified but never published",
                },
            },
        ],
    )
    assert store.search([0.1] * 8) == []

    # A properly published version IS retrievable.
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v["id"])
    service.publish(ctx, v["id"])
    hits = store.search([0.1] * 8)
    assert hits
    assert all(h["payload"]["published"] is True for h in hits)


def test_list_categories_reports_state(service, ctx):
    cats = service.list_categories(ctx)
    assert len(cats) == 10
    v = service.create_draft(ctx, category="faq", content=CONTENT_V1)
    service.verify(ctx, v["id"])
    service.publish(ctx, v["id"])
    by_cat: dict[str, Any] = {c["category"]: c for c in service.list_categories(ctx)}
    assert by_cat["faq"]["published"] is True
    assert by_cat["faq"]["verification_status"] == "verified"
    assert by_cat["rooms"]["document_id"] is None
