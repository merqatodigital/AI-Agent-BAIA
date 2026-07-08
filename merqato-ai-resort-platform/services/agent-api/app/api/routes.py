from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.knowledge.embeddings import EmbeddingNotConfigured
from app.models.schemas import (
    ConciergeRequest,
    ConciergeResponse,
    OpenRouterValidateRequest,
    OpenRouterValidateResponse,
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
