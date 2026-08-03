from __future__ import annotations

import os

import pytest

# Keep the unit suite offline and fast: CrewAI Flow kickoff otherwise tries to
# export telemetry spans over the network.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# These imports must follow the telemetry env setup above (crewai reads the
# environment at import time), hence the E402 suppressions.
from crewai import Crew  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import DEFAULT_TENANT_SLUG, get_settings  # noqa: E402
from app.knowledge.repository import (  # noqa: E402
    KnowledgeRepository,
    reset_default_backend,
)
from app.main import app  # noqa: E402


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


# The repo ships a real .env (Supabase creds, admin token) that must NEVER be
# used by the offline unit suite — tests are designed around the in-memory
# backend and a disabled admin API. Neutralize those env vars so a present
# .env does not silently route tests to the live DB or enable the admin API.
# Tests that need the real Supabase/admin path set these explicitly.
@pytest.fixture(autouse=True)
def _neutralize_local_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    yield


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
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter-00000000000000000000")
    # Embedding provider construction is validated fail-closed in production;
    # tests satisfy it with a dummy key (no network call is ever made because
    # Crew.kickoff is mocked).
    monkeypatch.setenv("OPENAI_API_KEY", "test-embedding-key")
