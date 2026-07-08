from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ConciergeRequest,
    ConciergeResponse,
    OpenRouterValidateRequest,
    OpenRouterValidateResponse,
)
from app.services.concierge_service import (
    OpenRouterNotConfigured,
    run_concierge,
)
from app.services.openrouter_validate import validate_openrouter_key

router = APIRouter()


@router.post("/v1/concierge/message", response_model=ConciergeResponse)
def concierge_message(req: ConciergeRequest) -> ConciergeResponse:
    try:
        return run_concierge(req)
    except OpenRouterNotConfigured as exc:
        # Controlled, clear error. No secrets, no fabricated answer.
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
