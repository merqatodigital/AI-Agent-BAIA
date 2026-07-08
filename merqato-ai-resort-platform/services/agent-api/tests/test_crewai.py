from __future__ import annotations

import os

import pytest
from crewai import LLM, Agent, Crew, Task

from app.crews.concierge import ConciergeCrew
from app.crews.concierge.crew import TenantKnowledgeTool
from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.qdrant_store import TenantQdrantStore
from app.services.tenant_resolver import (
    TenantResolutionError,
    make_tenant_context,
)

# Construction of a real CrewAI LLM validates API-key presence but makes no
# network call, so a dummy key is sufficient for unit construction.
_DUMMY_KEY = "sk-or-dummy-not-real"
os.environ.setdefault("OPENROUTER_API_KEY", _DUMMY_KEY)
os.environ.setdefault("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def test_real_crewai_imports_exist():
    # Proof that the ACTUAL crewai package is imported and used.
    assert all(callable(cls) for cls in (Agent, Task, Crew, LLM))


def test_concierge_crew_is_real_crewai_objects():
    ctx = make_tenant_context("11111111-1111-1111-1111-111111111111", "baia_resort", "active")
    tool = TenantKnowledgeTool(
        ctx, FakeEmbeddingProvider(), TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    )
    crew = ConciergeCrew(ctx, knowledge_tool=tool, embedder=FakeEmbeddingProvider()).build()
    # The returned object is a real CrewAI Crew built from real Agent+Task.
    assert isinstance(crew, Crew)
    assert len(crew.agents) == 1
    assert isinstance(crew.agents[0], Agent)
    assert len(crew.tasks) == 1
    assert isinstance(crew.tasks[0], Task)
    # OpenRouter is configured via provider="openrouter".
    assert crew.agents[0].llm.provider == "openrouter"
    assert crew.agents[0].llm.base_url == "https://openrouter.ai/api/v1"


def test_crew_requires_verified_tenant_context():
    # Passing None / a raw unverified id must fail closed.
    with pytest.raises(TenantResolutionError):
        ConciergeCrew(None)  # type: ignore[arg-type]
    with pytest.raises(TenantResolutionError):
        ConciergeCrew("baia_resort")  # type: ignore[arg-type]


def test_tenant_ingestion_tool_is_attached_at_construction():
    ctx = make_tenant_context("22222222-2222-2222-2222-222222222222", "baia_resort", "active")
    tool = TenantKnowledgeTool(
        ctx, FakeEmbeddingProvider(), TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    )
    crew = ConciergeCrew(ctx, knowledge_tool=tool, embedder=FakeEmbeddingProvider()).build()
    attached = crew.agents[0].tools
    assert len(attached) == 1
    assert isinstance(attached[0], TenantKnowledgeTool)
    # The tool's collection is bound to the verified tenant; no override possible.
    assert attached[0].collection_name == "merqato_tenant_baia_resort"


def test_kickoff_path_remains_intact(monkeypatch: pytest.MonkeyPatch):
    ctx = make_tenant_context("33333333-3333-3333-3333-333333333333", "baia_resort", "active")
    tool = TenantKnowledgeTool(
        ctx, FakeEmbeddingProvider(), TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    )

    class _FakeCrew:
        def kickoff(self, inputs):
            assert inputs["guest_message"]
            return type("R", (), {"raw": "Hi! How can I help at BAIA Resort?"})()

    monkeypatch.setattr(ConciergeCrew, "crew", lambda self: _FakeCrew())
    crew = ConciergeCrew(ctx, knowledge_tool=tool, embedder=FakeEmbeddingProvider())
    result = crew.kickoff({"guest_message": "hello"})
    assert "BAIA Resort" in result.raw
