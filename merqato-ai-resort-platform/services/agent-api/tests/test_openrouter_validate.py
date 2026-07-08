from __future__ import annotations

import json
from unittest import mock

FAKE_KEY = "sk-or-v1-abcdefghijklmnopqrstuvwxyz0123456789"


class _FakeResp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class _FakeHTTPError(Exception):
    def __init__(self, code: int, payload: dict) -> None:
        self.code = code
        self.reason = "error"
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_validate_success_returns_valid(client, caplog):
    with mock.patch("app.services.openrouter_validate.urllib.request.urlopen") as uo:
        uo.return_value.__enter__.return_value = _FakeResp(
            {"model": "openai/gpt-4o-mini"}
        )
        resp = client.post(
            "/v1/openrouter/validate",
            json={"api_key": FAKE_KEY, "model": "openai/gpt-4o-mini"},
        )
    body = resp.json()
    assert resp.status_code == 200
    assert body["valid"] is True
    assert body["message"] == "Connection successful"
    # The key must never be echoed back.
    assert FAKE_KEY not in json.dumps(body)


def test_validate_invalid_key_returns_safe_error(client, caplog):
    with mock.patch("app.services.openrouter_validate.urllib.request.urlopen") as uo:
        uo.side_effect = _FakeHTTPError(
            401, {"error": {"message": f"invalid key {FAKE_KEY}"}}
        )
        resp = client.post(
            "/v1/openrouter/validate", json={"api_key": FAKE_KEY}
        )
    body = resp.json()
    assert resp.status_code == 200
    assert body["valid"] is False
    # Provider error is redacted; the key must not surface.
    assert FAKE_KEY not in body["message"]
    assert FAKE_KEY not in json.dumps(body)
    assert "[REDACTED]" in caplog.text or FAKE_KEY not in caplog.text


def test_validate_key_never_in_logs(client, caplog):
    with mock.patch("app.services.openrouter_validate.urllib.request.urlopen") as uo:
        uo.return_value.__enter__.return_value = _FakeResp(
            {"model": "openai/gpt-4o-mini"}
        )
        client.post(
            "/v1/openrouter/validate",
            json={"api_key": FAKE_KEY, "model": "openai/gpt-4o-mini"},
        )
    # The fake key must not appear in captured logs in any form.
    assert FAKE_KEY not in caplog.text
