"""End-to-end proof over a TEST tenant (never live BAIA):

admin edit → immutable draft → verify → publish → Supabase publication →
Qdrant indexing → audit record → guest question → published-knowledge
retrieval → grounded CrewAI answer.

The LLM call is replaced by a stub that REALLY invokes the crew's attached
TenantKnowledgeTool, so retrieval flows through the genuine tool → store →
guest-safety filters. Embeddings and Qdrant are in-memory fakes; everything
else (routes, flow, crew construction, repositories, publishing) is real.
"""

from __future__ import annotations

from crewai import Crew

from app.config import DEFAULT_TENANT_SLUG
from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.repository import KnowledgeRepository
from tests.qdrant_fakes import FilterAwareVectorClient, make_store

TOKEN = "e2e-admin-token"
ADMIN = f"/v1/admin/tenants/{DEFAULT_TENANT_SLUG}/knowledge"
HEADERS = {"X-Admin-Token": TOKEN}
COLLECTION = "merqato_tenant_baia_resort"

FAQ_V1 = {
    "summary": "Airport pickup is available for 1500 PHP per van.",
    "items": [{"q": "Do you offer airport pickup?", "a": "Yes, 1500 PHP per van."}],
}
FAQ_V2_DRAFT = {
    "summary": "SECRET DRAFT: pickup price will rise to 2000 PHP next month.",
    "items": [{"q": "Draft only", "a": "Not yet approved."}],
}


def _wire_fakes(monkeypatch, vector_client: FilterAwareVectorClient) -> None:
    """Point BOTH the admin publish path and the guest flow at the same
    in-memory embeddings + Qdrant."""
    import app.api.knowledge_routes as kr
    import app.crews.concierge.flow as flow_mod

    embedder = FakeEmbeddingProvider(dimension=8)
    monkeypatch.setattr(kr, "get_embedding_provider", lambda: embedder)
    monkeypatch.setattr(flow_mod, "get_embedding_provider", lambda: embedder)
    monkeypatch.setattr(
        kr,
        "TenantQdrantStore",
        lambda tid, slug: make_store(tid, slug, client=vector_client),
    )
    monkeypatch.setattr(
        flow_mod,
        "TenantQdrantStore",
        lambda tid, slug: make_store(tid, slug, client=vector_client),
    )


def _grounded_kickoff(monkeypatch) -> list[str]:
    """CrewAI kickoff stub that actually calls the attached tenant knowledge
    tool — the reply is grounded in whatever retrieval returns."""
    retrieved: list[str] = []

    def fake_kickoff(self, inputs=None):  # noqa: ANN001
        tool = self.agents[0].tools[0]
        knowledge = tool._run(inputs["guest_message"])
        retrieved.append(knowledge)

        class _Out:
            raw = f"Based on our resort knowledge: {knowledge} intent: faq confidence: 0.9"

        return _Out()

    monkeypatch.setattr(Crew, "kickoff", fake_kickoff)
    return retrieved


def _guest_ask(client, message: str):
    return client.post(
        "/v1/concierge/message",
        json={
            "resort_id": DEFAULT_TENANT_SLUG,
            "conversation_id": "e2e-1",
            "message": message,
            "locale": "en",
        },
    )


def test_full_admin_to_guest_chain(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", TOKEN)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-e2e-not-real")
    vectors = FilterAwareVectorClient(dimension=8)
    _wire_fakes(monkeypatch, vectors)
    retrieved = _grounded_kickoff(monkeypatch)

    repo = KnowledgeRepository()
    tenant = repo.upsert_tenant(
        slug=DEFAULT_TENANT_SLUG,
        business_name="BAIA Resort (test)",
        business_type="resort",
        status="active",
    )

    # 1. admin edit → immutable draft
    r = client.post(f"{ADMIN}/faq/draft", headers=HEADERS, json={"content": FAQ_V1})
    assert r.status_code == 200
    v1 = r.json()
    assert v1["verification_status"] == "draft" and v1["published_at"] is None
    # draft is NOT indexed
    assert vectors.all_points(COLLECTION) == []

    # 2. guest asks while only a draft exists → no draft leakage
    r = _guest_ask(client, "Do you offer airport pickup?")
    assert r.status_code == 200
    assert "1500" not in r.json()["reply"]
    assert retrieved[-1] == "(no tenant knowledge found)"

    # 3. verify → publish
    r = client.post(f"{ADMIN}/versions/{v1['id']}/verify", headers=HEADERS,
                    json={"actor_id": "owner@test"})
    assert r.status_code == 200
    r = client.post(f"{ADMIN}/versions/{v1['id']}/publish", headers=HEADERS, json={})
    assert r.status_code == 200
    published = r.json()

    # 4. Supabase publication recorded
    stored = repo.get_version(v1["id"])
    assert stored is not None
    assert stored["published_at"] == published["published_at"] is not None

    # 5. Qdrant indexing with publication metadata
    points = vectors.all_points(COLLECTION)
    assert points
    assert all(p["payload"]["published"] is True for p in points)
    assert all(p["payload"]["document_version_id"] == v1["id"] for p in points)

    # 6. audit records for the whole lifecycle
    actions = [a["action"] for a in repo.list_audits(tenant["id"])]
    assert {"create_draft", "verify_version", "publish_version"} <= set(actions)

    # 7. ingestion job linked to the exact version, completed
    jobs = repo.list_jobs(tenant["id"], document_version_id=v1["id"])
    assert jobs and jobs[0]["status"] == "completed" and jobs[0]["chunks_created"] > 0

    # 8. guest question → published knowledge retrieval → grounded answer
    r = _guest_ask(client, "Do you offer airport pickup?")
    assert r.status_code == 200
    body = r.json()
    assert "1500 PHP" in body["reply"]  # grounded in published content
    assert body["conversation_id"] == "e2e-1"
    assert "1500" in retrieved[-1]

    # 9. a NEWER unverified draft never reaches guests
    r = client.post(f"{ADMIN}/faq/draft", headers=HEADERS, json={"content": FAQ_V2_DRAFT})
    assert r.status_code == 200
    r = _guest_ask(client, "Will the pickup price change?")
    assert "2000" not in r.json()["reply"]
    assert "SECRET DRAFT" not in r.json()["reply"]

    # 10. unpublish removes guest access again
    r = client.post(f"{ADMIN}/versions/{v1['id']}/unpublish", headers=HEADERS, json={})
    assert r.status_code == 200
    r = _guest_ask(client, "Do you offer airport pickup?")
    assert "1500" not in r.json()["reply"]
    assert retrieved[-1] == "(no tenant knowledge found)"


def test_internal_content_cannot_be_published_or_leaked(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", TOKEN)
    vectors = FilterAwareVectorClient(dimension=8)
    _wire_fakes(monkeypatch, vectors)
    KnowledgeRepository().upsert_tenant(
        slug=DEFAULT_TENANT_SLUG, business_name="BAIA Resort (test)",
        business_type="resort", status="active",
    )
    r = client.post(
        f"{ADMIN}/policies/draft",
        headers=HEADERS,
        json={
            "content": {"summary": "INTERNAL: staff gate code is 4321"},
            "guest_visible": False,
            "internal_only": True,
        },
    )
    assert r.status_code == 200
    vid = r.json()["id"]
    client.post(f"{ADMIN}/versions/{vid}/verify", headers=HEADERS, json={})
    r = client.post(f"{ADMIN}/versions/{vid}/publish", headers=HEADERS, json={})
    assert r.status_code == 422  # publishing internal content is impossible
    assert vectors.all_points(COLLECTION) == []


def test_no_cross_tenant_retrieval(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", TOKEN)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-e2e-not-real")
    vectors = FilterAwareVectorClient(dimension=8)
    _wire_fakes(monkeypatch, vectors)
    retrieved = _grounded_kickoff(monkeypatch)

    repo = KnowledgeRepository()
    repo.upsert_tenant(
        slug=DEFAULT_TENANT_SLUG, business_name="BAIA Resort (test)",
        business_type="resort", status="active",
    )
    repo.upsert_tenant(
        slug="other-resort", business_name="Other Resort",
        business_type="resort", status="active",
    )

    # publish content ONLY for the other tenant
    other = "/v1/admin/tenants/other-resort/knowledge"
    r = client.post(f"{other}/faq/draft", headers=HEADERS,
                    json={"content": {"summary": "Other resort serves free tequila."}})
    vid = r.json()["id"]
    client.post(f"{other}/versions/{vid}/verify", headers=HEADERS, json={})
    r = client.post(f"{other}/versions/{vid}/publish", headers=HEADERS, json={})
    assert r.status_code == 200
    assert vectors.all_points("merqato_tenant_other_resort")

    # guest of baia-resort can never retrieve the other tenant's knowledge
    r = _guest_ask(client, "Do you serve free tequila?")
    assert r.status_code == 200
    assert "tequila" not in r.json()["reply"].lower()
    assert retrieved[-1] == "(no tenant knowledge found)"


def test_safe_failure_when_credentials_missing(client, monkeypatch):
    """Missing secrets always produce controlled 5xx, never crashes/fabrication."""
    repo = KnowledgeRepository()
    repo.upsert_tenant(
        slug=DEFAULT_TENANT_SLUG, business_name="BAIA Resort (test)",
        business_type="resort", status="active",
    )
    # no ADMIN_API_TOKEN → admin API disabled
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
    assert client.get(f"{ADMIN}/categories", headers=HEADERS).status_code == 503

    # no OpenRouter key → concierge 503 with clear detail
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()
    r = _guest_ask(client, "Hello")
    assert r.status_code == 503

    # OpenRouter present but embeddings missing → still a controlled 503
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-e2e-not-real")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    r = _guest_ask(client, "Hello")
    assert r.status_code == 503
