from __future__ import annotations

from app.config import get_settings


def _payload(*messages: tuple[str, str], stream: bool = False) -> dict[str, object]:
    return {
        "model": "tala-agent",
        "messages": [{"role": role, "content": content} for role, content in messages],
        "stream": stream,
    }


def test_voice_adapter_runs_existing_tala_flow(
    mock_crew_kickoff, set_openrouter_key, baia_tenant, client
):
    response = client.post(
        "/v1/chat/completions",
        json=_payload(
            ("system", "You are TALA."),
            ("user", "Do you have WiFi?"),
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert "Front desk is open 24/7" in body["choices"][0]["message"]["content"]
    assert len(mock_crew_kickoff) == 1
    prompt = mock_crew_kickoff[0]["guest_message"]
    assert "live voice conversation" in prompt
    assert "Guest: Do you have WiFi?" in prompt


def test_voice_adapter_preserves_recent_conversation(
    mock_crew_kickoff, set_openrouter_key, baia_tenant, client
):
    response = client.post(
        "/v1/chat/completions",
        json=_payload(
            ("user", "Do you arrange airport transfers?"),
            ("assistant", "Yes, staff can help arrange one."),
            ("user", "How long does it take?"),
        ),
    )

    assert response.status_code == 200
    prompt = mock_crew_kickoff[0]["guest_message"]
    assert "Guest: Do you arrange airport transfers?" in prompt
    assert "TALA: Yes, staff can help arrange one." in prompt
    assert "Guest: How long does it take?" in prompt


def test_voice_adapter_rejects_streaming(client):
    response = client.post(
        "/v1/chat/completions",
        json=_payload(("user", "Hello"), stream=True),
    )
    assert response.status_code == 400


def test_voice_adapter_requires_secret_outside_development(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("VOICE_INTERNAL_API_KEY", "voice-secret")
    get_settings.cache_clear()
    try:
        unauthorized = client.post(
            "/v1/chat/completions",
            json=_payload(("user", "Hello")),
        )
        assert unauthorized.status_code == 401

        authorized = client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer voice-secret"},
            json=_payload(("user", "Hello")),
        )
        # Auth passed; the test intentionally has no OpenRouter key.
        assert authorized.status_code == 503
    finally:
        get_settings.cache_clear()
