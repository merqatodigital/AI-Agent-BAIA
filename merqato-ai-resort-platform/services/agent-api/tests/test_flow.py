"""ConciergeFlow — the CrewAI Flow wrapping the existing ConciergeCrew."""

from __future__ import annotations

import pytest
from crewai.flow.flow import Flow

from app.config import DEFAULT_TENANT_SLUG
from app.crews.concierge.flow import (
    ConciergeFlow,
    OpenRouterNotConfigured,
    TenantNotResolvable,
)
from app.knowledge.repository import KnowledgeRepository
from app.models.schemas import ConciergeRequest
from app.services.concierge_service import run_concierge


def _req(message: str = "What time is breakfast?") -> ConciergeRequest:
    return ConciergeRequest(
        resort_id=DEFAULT_TENANT_SLUG,
        conversation_id="conv-42",
        message=message,
        locale="en",
    )


def test_concierge_flow_is_a_real_crewai_flow():
    assert issubclass(ConciergeFlow, Flow)


def test_flow_runs_crew_and_preserves_conversation_id(
    mock_crew_kickoff, set_openrouter_key, baia_tenant
):
    resp = run_concierge(_req())
    assert "Front desk is open 24/7" in resp.reply
    assert resp.intent == "hours_question"
    assert resp.conversation_id == "conv-42"
    assert mock_crew_kickoff == [{"guest_message": "What time is breakfast?"}]


def test_flow_fails_closed_without_openrouter_key(baia_tenant, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    # The tenant fixture already re-populated the settings cache; drop it so
    # the flow observes the missing key.
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(OpenRouterNotConfigured):
        run_concierge(_req())


def test_flow_fails_closed_for_unknown_tenant(set_openrouter_key):
    with pytest.raises(TenantNotResolvable):
        run_concierge(_req())  # tenant never seeded


def test_flow_fails_closed_for_draft_tenant(set_openrouter_key):
    KnowledgeRepository().upsert_tenant(
        slug=DEFAULT_TENANT_SLUG,
        business_name="BAIA Resort",
        business_type="resort",
        status="draft",
    )
    with pytest.raises(TenantNotResolvable):
        run_concierge(_req())


def test_flow_safety_step_flags_forbidden_reply(
    mock_kickoff_with, set_openrouter_key, baia_tenant
):
    mock_kickoff_with("Sure, I have confirmed your booking. intent: booking confidence: 0.9")
    resp = run_concierge(_req("Confirm my booking please"))
    assert resp.requires_approval is True
    assert "forbidden_action" in (resp.escalation_reason or "")
