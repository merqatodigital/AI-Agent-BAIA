from __future__ import annotations

from app.crews.concierge.flow import (
    ConciergeFlow,
    OpenRouterNotConfigured,
    TenantNotResolvable,
)
from app.models.schemas import ConciergeRequest, ConciergeResponse

__all__ = [
    "OpenRouterNotConfigured",
    "TenantNotResolvable",
    "run_concierge",
]


def run_concierge(req: ConciergeRequest) -> ConciergeResponse:
    """Run the guest concierge pipeline via the CrewAI Flow.

    The Flow (app.crews.concierge.flow.ConciergeFlow) owns orchestration:
    credentials gate → tenant resolution → ConciergeCrew execution → safety
    validation. This service adapts the API request/response contract and
    preserves conversation_id untouched (no fabricated memory).
    """
    flow = ConciergeFlow()
    flow.kickoff(
        inputs={
            "resort_id": req.resort_id,
            "conversation_id": req.conversation_id,
            "message": req.message,
            "locale": req.locale,
        }
    )
    s = flow.state
    return ConciergeResponse(
        reply=s.reply,
        intent=s.intent,
        confidence=s.confidence,
        sources=[],
        proposed_actions=[],
        requires_approval=s.requires_approval,
        escalation_reason=s.escalation_reason,
        conversation_id=s.conversation_id,
    )
