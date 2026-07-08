from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.config import get_settings
from app.models.schemas import OpenRouterValidateRequest, OpenRouterValidateResponse
from app.security.secrets import redact, safe_log

logger = logging.getLogger("merqato.openrouter")

_VALIDATE_TIMEOUT_SECONDS = 15


def validate_openrouter_key(
    req: OpenRouterValidateRequest,
) -> OpenRouterValidateResponse:
    """Validate a customer-supplied OpenRouter key with a minimal request.

    The key is treated as TRANSIENT: it is used only for this single request,
    never stored, never logged, and never returned. Provider error text is
    redacted before being surfaced to the caller.
    """
    settings = get_settings()
    model = req.model or settings.openrouter_model
    base_url = settings.openrouter_base_url.rstrip("/")

    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }
    ).encode("utf-8")

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {req.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://merqato.ai",
        "X-Title": "MerQato AI Resort Website",
    }

    request = urllib.request.Request(
        url, data=payload, headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(
            request, timeout=_VALIDATE_TIMEOUT_SECONDS
        ) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            used_model = body.get("model") or model
            return OpenRouterValidateResponse(
                valid=True,
                model=used_model,
                message="Connection successful",
            )
    except urllib.error.HTTPError as exc:
        detail = _safe_detail(exc)
        safe_log(f"OpenRouter validation failed (HTTP {exc.code}): {detail}")
        return OpenRouterValidateResponse(
            valid=False,
            model=None,
            message=f"OpenRouter rejected the key (HTTP {exc.code}).",
        )
    except urllib.error.URLError as exc:
        safe_log(f"OpenRouter validation unreachable: {redact(str(exc.reason))}")
        return OpenRouterValidateResponse(
            valid=False,
            model=None,
            message="Could not reach OpenRouter. Check network connectivity.",
        )
    except Exception as exc:  # noqa: BLE001 - surface a safe, redacted message
        safe_log(f"OpenRouter validation error: {redact(str(exc))}")
        return OpenRouterValidateResponse(
            valid=False,
            model=None,
            message="Validation failed due to an unexpected error.",
        )


def _safe_detail(exc: urllib.error.HTTPError) -> str:
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        return redact(payload.get("error", {}).get("message", exc.reason or ""))
    except Exception:  # noqa: BLE001
        return redact(str(exc.reason or ""))
