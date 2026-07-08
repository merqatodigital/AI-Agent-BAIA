from __future__ import annotations

import hashlib
import logging
import re

logger = logging.getLogger("app.security")

# Patterns that look like secrets. Used to scrub error messages before they
# are persisted to the audit log or returned to callers. Never store the raw
# value of any of these.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"sk-or-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{8,}"),
    re.compile(r"api[_-]?key[=:\s]+[^\s\"']{8,}", re.IGNORECASE),
    re.compile(r"token[=:\s]+[^\s\"']{8,}", re.IGNORECASE),
    re.compile(r"password[=:\s]+[^\s\"']{8,}", re.IGNORECASE),
    # JSON Web Tokens: three dot-separated base64url segments.
    re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
)


def redact(text: str) -> str:
    """Replace any secret-like substrings with the literal ``[REDACTED]``."""
    cleaned = text
    for pat in _SECRET_PATTERNS:
        cleaned = pat.sub("[REDACTED]", cleaned)
    return cleaned


def safe_log(message: str) -> None:
    """Log a message with any embedded secret redacted first."""
    logger.info(redact(message))


def hash_secret(raw: str) -> str:
    """Return a stable, irreversible hash of a secret (e.g. a widget token).

    The raw value is never persisted; only the ``sha256:`` digest is stored.
    """
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
