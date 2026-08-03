from __future__ import annotations

import json
import logging

from app.services.concierge_service import run_concierge  # noqa: F401


def test_concierge_executes_through_crewai(
    mock_crew_kickoff, set_openrouter_key, baia_tenant, client
):
    r = client.post(
        "/v1/concierge/message",
        json={
            "resort_id": baia_tenant,
            "conversation_id": "c1",
            "message": "What are your front desk hours?",
            "locale": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "Front desk is open 24/7" in body["reply"]
    assert body["intent"] == "hours_question"
    assert body["confidence"] == 0.9
    # Proves the real CrewAI kickoff was invoked with the guest message.
    assert mock_crew_kickoff == [{"guest_message": "What are your front desk hours?"}]


def test_missing_openrouter_returns_controlled_error(baia_tenant, client, monkeypatch, caplog):
    # Force the configured key to be absent so the 503 path is exercised.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY_RAW", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()
    with caplog.at_level(logging.INFO):
        r = client.post(
            "/v1/concierge/message",
            json={
                "resort_id": baia_tenant,
                "conversation_id": "c1",
                "message": "Hello",
                "locale": "en",
            },
        )
    assert r.status_code == 503
    assert "OpenRouter is not configured" in r.json()["detail"]


def test_unknown_information_not_invented(
    mock_kickoff_with, set_openrouter_key, baia_tenant, client
):
    mock_kickoff_with(
        "I do not have that information in the resort knowledge. "
        "intent: unknown confidence: 0.2"
    )
    r = client.post(
        "/v1/concierge/message",
        json={
            "resort_id": baia_tenant,
            "conversation_id": "c1",
            "message": "Do you have a submarine?",
            "locale": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "do not have" in body["reply"].lower()
    assert body["confidence"] <= 0.3


def test_forbidden_action_requires_approval(
    mock_kickoff_with, set_openrouter_key, baia_tenant, client
):
    mock_kickoff_with(
        "Sure, I have confirmed your booking. intent: booking confidence: 0.9"
    )
    r = client.post(
        "/v1/concierge/message",
        json={
            "resort_id": baia_tenant,
            "conversation_id": "c1",
            "message": "Confirm my booking please",
            "locale": "en",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["requires_approval"] is True
    assert "forbidden_action" in (body["escalation_reason"] or "")


def test_openrouter_key_never_in_response_or_logs(
    mock_crew_kickoff, set_openrouter_key, baia_tenant, client, caplog
):
    with caplog.at_level(logging.INFO):
        r = client.post(
            "/v1/concierge/message",
            json={
                "resort_id": baia_tenant,
                "conversation_id": "c1",
                "message": "Hi",
                "locale": "en",
            },
        )
    assert r.status_code == 200
    dumped = json.dumps(r.json())
    assert "sk-test-openrouter-00000000000000000000" not in dumped
    assert "sk-test-openrouter-00000000000000000000" not in caplog.text
