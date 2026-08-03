"""Guest concierge service entry point.

This module exposes the public API that routes call. Historically it invoked
ConciergeFlow directly; it now delegates to Hermes, BAIA's guest-facing agent.
"""

from __future__ import annotations

from app.agents.hermes import Hermes
from app.crews.concierge.flow import (
    OpenRouterNotConfigured,
    TenantNotResolvable,
)
from app.models.schemas import ConciergeRequest, ConciergeResponse

__all__ = [
    "OpenRouterNotConfigured",
    "TenantNotResolvable",
    "run_concierge",
]


_sync_hermes = Hermes()


def run_concierge(req: ConciergeRequest) -> ConciergeResponse:
    """Run the guest concierge pipeline through Hermes.

    Hermes (app.agents.hermes) wraps the CrewAI ConciergeCrew with BAIA's
    persona, skill routing, safety boundaries, and typed response contract.
    The conversation_id is preserved untouched; Hermes does not fabricate
    server-side memory.
    """
    return _sync_hermes.assist(req)
