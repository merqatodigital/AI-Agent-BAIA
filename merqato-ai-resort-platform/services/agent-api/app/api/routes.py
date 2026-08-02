from __future__ import annotations

import secrets
import time
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from app.config import DEFAULT_TENANT_SLUG, get_settings
from app.knowledge.embeddings import EmbeddingNotConfigured
from app.models.schemas import (
    ConciergeRequest,
    ConciergeResponse,
    OpenRouterValidateRequest,
    OpenRouterValidateResponse,
    VoiceChatCompletionRequest,
)
from app.security.secrets import safe_log
from app.services.concierge_service import (
    OpenRouterNotConfigured,
    TenantNotResolvable,
    run_concierge,
)
from app.services.openrouter_validate import validate_openrouter_key

router = APIRouter()

_UNAVAILABLE_REPLY = (
    "The concierge is not available for this resort right now. "
    "Please contact the resort directly."
)


def _safe_unavailable(req: ConciergeRequest, reason: str) -> JSONResponse:
    """Controlled response for draft/inactive/unknown tenants.

    Never leaks tenant existence or status details to the guest; the reason
    stays in server logs only.
    """
    safe_log(f"concierge unavailable for resort {req.resort_id!r}: {reason}")
    body = ConciergeResponse(
        reply=_UNAVAILABLE_REPLY,
        intent="service_unavailable",
        confidence=0.0,
        requires_approval=False,
        escalation_reason="tenant_unavailable",
        conversation_id=req.conversation_id,
    )
    return JSONResponse(status_code=503, content=body.model_dump())


def _voice_api_authorized(authorization: str | None) -> bool:
    settings = get_settings()
    expected = settings.voice_internal_api_key
    if not expected:
        return settings.environment == "development"
    if not authorization or not authorization.startswith("Bearer "):
        return False
    return secrets.compare_digest(authorization.removeprefix("Bearer ").strip(), expected)


def _message_text(content: str | list[dict[str, object]] | None) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for part in content:
        if part.get("type") not in {"text", "input_text"}:
            continue
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return " ".join(parts)


def _tala_voice_prompt(req: VoiceChatCompletionRequest) -> str:
    """Preserve enough recent context for a natural voice turn.

    The existing ConciergeFlow remains the sole agent engine. This adapter
    converts speech-to-speech's Chat Completions history into one grounded
    guest message rather than creating a second LLM brain.
    """
    turns: list[str] = []
    for message in req.messages:
        text = _message_text(message.content)
        if not text or message.role not in {"user", "assistant"}:
            continue
        speaker = "Guest" if message.role == "user" else "TALA"
        turns.append(f"{speaker}: {text}")
    if not turns:
        raise HTTPException(status_code=400, detail="A user message is required")
    recent = turns[-8:]
    return (
        "You are replying in a live voice conversation. Keep the answer natural, "
        "warm, and concise unless the guest asks for detail. Never claim a booking "
        "or payment is confirmed; follow all normal TALA safety rules.\n\n"
        "Recent conversation:\n" + "\n".join(recent)
    )


@router.post("/v1/concierge/message", response_model=ConciergeResponse)
def concierge_message(req: ConciergeRequest) -> ConciergeResponse | JSONResponse:
    try:
        return run_concierge(req)
    except OpenRouterNotConfigured as exc:
        # Controlled, clear error. No secrets, no fabricated answer.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EmbeddingNotConfigured as exc:
        # Fail closed: no fake embeddings, no fabricated retrieval.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TenantNotResolvable as exc:
        # Draft/suspended/archived/unknown tenants get a safe reply, not a 500.
        return _safe_unavailable(req, str(exc))


@router.post("/v1/chat/completions")
def tala_voice_chat_completion(
    req: VoiceChatCompletionRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """OpenAI-compatible, non-streaming adapter for Hugging Face voice.

    speech-to-speech owns VAD, transcription, turn-taking, and synthesis. The
    response itself still comes from the existing CrewAI ConciergeFlow.
    """
    if not _voice_api_authorized(authorization):
        raise HTTPException(status_code=401, detail="Invalid voice service credentials")
    if req.stream:
        raise HTTPException(
            status_code=400,
            detail="Streaming is disabled for the TALA voice adapter",
        )

    concierge_req = ConciergeRequest(
        resort_id=DEFAULT_TENANT_SLUG,
        conversation_id=f"voice-{uuid4()}",
        message=_tala_voice_prompt(req),
        locale="en",
    )
    try:
        result = run_concierge(concierge_req)
    except OpenRouterNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EmbeddingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TenantNotResolvable as exc:
        safe_log(f"voice concierge unavailable: {exc}")
        raise HTTPException(status_code=503, detail="TALA is unavailable") from exc

    return {
        "id": f"chatcmpl-{uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "tala-agent",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": result.reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@router.post(
    "/v1/openrouter/validate",
    response_model=OpenRouterValidateResponse,
)
def openrouter_validate(
    req: OpenRouterValidateRequest,
) -> OpenRouterValidateResponse:
    """Validate a transient customer OpenRouter key.

    The key is used only for this request and is never stored, logged, or
    returned. Provider errors are redacted before being surfaced.
    """
    return validate_openrouter_key(req)
