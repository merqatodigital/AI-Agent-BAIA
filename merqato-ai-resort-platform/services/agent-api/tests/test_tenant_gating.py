"""Route-level safe handling of draft, inactive and unknown tenants."""

from __future__ import annotations

import pytest

from app.config import DEFAULT_TENANT_SLUG
from app.knowledge.repository import KnowledgeRepository


def _post(client, resort_id: str = DEFAULT_TENANT_SLUG):
    return client.post(
        "/v1/concierge/message",
        json={
            "resort_id": resort_id,
            "conversation_id": "conv-7",
            "message": "Do you have rooms available?",
            "locale": "en",
        },
    )


def _seed(status: str) -> None:
    KnowledgeRepository().upsert_tenant(
        slug=DEFAULT_TENANT_SLUG,
        business_name="BAIA Resort",
        business_type="resort",
        status=status,
    )


@pytest.mark.parametrize("status", ["draft", "suspended", "archived"])
def test_non_active_tenant_gets_safe_unavailable_response(
    status, set_openrouter_key, client
):
    _seed(status)
    r = _post(client)
    assert r.status_code == 503
    body = r.json()
    assert body["intent"] == "service_unavailable"
    assert body["escalation_reason"] == "tenant_unavailable"
    assert body["conversation_id"] == "conv-7"
    # The safe reply must not leak tenant lifecycle details.
    assert status not in body["reply"].lower()


def test_unknown_tenant_gets_safe_unavailable_response(set_openrouter_key, client):
    r = _post(client, resort_id="does-not-exist")
    assert r.status_code == 503
    body = r.json()
    assert body["intent"] == "service_unavailable"
    assert "does-not-exist" not in body["reply"]


def test_active_tenant_still_served(
    mock_crew_kickoff, set_openrouter_key, baia_tenant, client
):
    r = _post(client)
    assert r.status_code == 200
    assert r.json()["conversation_id"] == "conv-7"
