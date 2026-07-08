"""Admin knowledge-management routes: auth, tenant scoping, lifecycle."""

from __future__ import annotations

import pytest

from app.config import DEFAULT_TENANT_SLUG
from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.repository import KnowledgeRepository
from tests.qdrant_fakes import FilterAwareVectorClient, make_store

TOKEN = "test-admin-token"
BASE = f"/v1/admin/tenants/{DEFAULT_TENANT_SLUG}/knowledge"
HEADERS = {"X-Admin-Token": TOKEN}


@pytest.fixture
def admin_env(monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", TOKEN)


@pytest.fixture
def draft_tenant():
    """BAIA-like tenant in DRAFT status — admin must still manage it."""
    KnowledgeRepository().upsert_tenant(
        slug=DEFAULT_TENANT_SLUG,
        business_name="BAIA Resort",
        business_type="resort",
        status="draft",
    )


@pytest.fixture
def fake_vectors(monkeypatch):
    """Route publish path wired to in-memory embeddings + Qdrant."""
    client_store = FilterAwareVectorClient(dimension=8)
    import app.api.knowledge_routes as kr

    monkeypatch.setattr(kr, "get_embedding_provider", lambda: FakeEmbeddingProvider(dimension=8))
    monkeypatch.setattr(
        kr,
        "TenantQdrantStore",
        lambda tenant_id, slug: make_store(tenant_id, slug, client=client_store),
    )
    return client_store


CONTENT = {"summary": "Check-in from 2pm", "policies": ["No smoking"]}


def test_routes_fail_closed_without_configured_token(client, draft_tenant):
    r = client.get(f"{BASE}/categories", headers=HEADERS)
    assert r.status_code == 503  # ADMIN_API_TOKEN not configured


def test_routes_reject_bad_token(client, admin_env, draft_tenant):
    assert client.get(f"{BASE}/categories").status_code == 401
    r = client.get(f"{BASE}/categories", headers={"X-Admin-Token": "wrong"})
    assert r.status_code == 401


def test_unknown_tenant_404(client, admin_env):
    r = client.get(
        "/v1/admin/tenants/nope/knowledge/categories", headers=HEADERS
    )
    assert r.status_code == 404


def test_categories_listing(client, admin_env, draft_tenant):
    r = client.get(f"{BASE}/categories", headers=HEADERS)
    assert r.status_code == 200
    cats = r.json()
    assert len(cats) == 10
    assert {c["category"] for c in cats} >= {"identity", "rooms", "faq"}


def test_full_lifecycle_via_routes(client, admin_env, draft_tenant, fake_vectors):
    # draft
    r = client.post(f"{BASE}/policies/draft", headers=HEADERS, json={"content": CONTENT})
    assert r.status_code == 200
    version = r.json()
    assert version["verification_status"] == "draft"
    vid = version["id"]

    # duplicate content → 409
    r = client.post(f"{BASE}/policies/draft", headers=HEADERS, json={"content": CONTENT})
    assert r.status_code == 409

    # publish before verify → 422
    r = client.post(f"{BASE}/versions/{vid}/publish", headers=HEADERS, json={})
    assert r.status_code == 422

    # verify
    r = client.post(
        f"{BASE}/versions/{vid}/verify", headers=HEADERS, json={"actor_id": "owner@baia"}
    )
    assert r.status_code == 200
    assert r.json()["verification_status"] == "verified"

    # publish
    r = client.post(f"{BASE}/versions/{vid}/publish", headers=HEADERS, json={})
    assert r.status_code == 200
    assert r.json()["published_at"] is not None
    assert fake_vectors.all_points("merqato_tenant_baia_resort")

    # current
    r = client.get(f"{BASE}/policies/current", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["version"]["id"] == vid

    # history + audits + jobs
    assert client.get(f"{BASE}/policies/versions", headers=HEADERS).json()
    audits = client.get(f"{BASE}/policies/audits", headers=HEADERS).json()
    assert {"create_draft", "verify_version", "publish_version"} <= {
        a["action"] for a in audits
    }
    jobs = client.get(f"{BASE}/jobs", headers=HEADERS, params={"version_id": vid}).json()
    assert jobs and jobs[0]["status"] == "completed"

    # unpublish
    r = client.post(f"{BASE}/versions/{vid}/unpublish", headers=HEADERS, json={})
    assert r.status_code == 200
    assert r.json()["published_at"] is None
    assert fake_vectors.all_points("merqato_tenant_baia_resort") == []


def test_publish_fails_closed_without_embeddings(client, admin_env, draft_tenant, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("KNOWLEDGE_EMBEDDING_PROVIDER", "openai")
    # The baia_tenant fixture already populated the lru-cached settings with
    # the .env defaults; clear so the provider override above takes effect.
    from app.config import get_settings

    get_settings.cache_clear()
    r = client.post(f"{BASE}/faq/draft", headers=HEADERS, json={"content": CONTENT})
    vid = r.json()["id"]
    client.post(f"{BASE}/versions/{vid}/verify", headers=HEADERS, json={})
    r = client.post(f"{BASE}/versions/{vid}/publish", headers=HEADERS, json={})
    assert r.status_code == 503


def test_unsupported_category_404(client, admin_env, draft_tenant):
    r = client.post(f"{BASE}/nonsense/draft", headers=HEADERS, json={"content": CONTENT})
    assert r.status_code == 404
