from __future__ import annotations

import pytest
from crewai import Crew
from fastapi.testclient import TestClient

from app.config import DEFAULT_TENANT_SLUG, get_settings
from app.knowledge.repository import KnowledgeRepository, reset_default_backend
from app.main import app


class _FakeCrewOutput:
    def __init__(self, raw: str) -> None:
        self.raw = raw


@pytest.fixture(autouse=True)
def _isolate_settings():
    # get_settings() is lru_cached; clear it so each test sees a fresh env.
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_knowledge_backend():
    # Keep the shared default in-memory backend isolated between tests.
    reset_default_backend()
    yield
    reset_default_backend()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def baia_tenant():
    """Seed an ACTIVE canonical tenant so the concierge service can resolve it."""
    repo = KnowledgeRepository()
    repo.upsert_tenant(
        slug=DEFAULT_TENANT_SLUG,
        business_name="BAIA Resort",
        business_type="resort",
        status="active",
    )
    yield DEFAULT_TENANT_SLUG


@pytest.fixture
def mock_crew_kickoff(monkeypatch):
    """Replaces CrewAI's real LLM call with a deterministic stub.

    Proves the concierge endpoint executes *through* the CrewAI service (the
    real Crew/Agent/Task objects are still constructed) without spending
    OpenRouter credits.
    """
    calls: list = []

    def fake_kickoff(self, inputs=None):  # noqa: ANN001
        calls.append(inputs)
        return _FakeCrewOutput(
            "Front desk is open 24/7. intent: hours_question confidence: 0.9"
        )

    monkeypatch.setattr(Crew, "kickoff", fake_kickoff)
    return calls


@pytest.fixture
def mock_kickoff_with(monkeypatch):
    """Returns a helper to make CrewAI kickoff return a given reply."""

    def _set(reply: str):
        def fake_kickoff(self, inputs=None):  # noqa: ANN001
            return _FakeCrewOutput(reply)

        monkeypatch.setattr(Crew, "kickoff", fake_kickoff)

    return _set


@pytest.fixture
def set_openrouter_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "«redacted:sk-…»")
