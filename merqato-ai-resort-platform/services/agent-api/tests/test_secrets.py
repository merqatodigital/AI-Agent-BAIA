from __future__ import annotations

from app.security.secrets import redact


def test_redact_masks_openrouter_key():
    s = redact("calling with sk-or-abc123def456ghi and done")
    assert "sk-or-abc123def456ghi" not in s
    assert "[REDACTED]" in s


def test_redact_masks_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    assert redact(jwt) == "[REDACTED]"


def test_redact_passthrough_safe_text():
    assert redact("front desk is open 24/7") == "front desk is open 24/7"
