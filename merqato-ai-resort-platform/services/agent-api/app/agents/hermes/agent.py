"""Hermes agent runtime."""

from __future__ import annotations

from app.agents.hermes.memory import TurnContext
from app.agents.hermes.orchestrator import HermesOrchestrator
from app.agents.hermes.persona import Persona
from app.agents.hermes.skills import decide_skill
from app.models.schemas import ConciergeRequest, ConciergeResponse


class Hermes:
    """BAIA's guest-facing AI concierge.

    Hermes wraps the underlying CrewAI ConciergeCrew and enforces:
      - the BAIA persona and tone
      - skill-based routing (booking, local rec, service, complaint, etc.)
      - verified-knowledge-only answers
      - safe escalation for actions he may not perform autonomously
    """

    def __init__(self) -> None:
        self.persona = Persona()
        self.orchestrator = HermesOrchestrator()

    def assist(self, req: ConciergeRequest) -> ConciergeResponse:
        """Handle one guest message and return a typed response."""
        decision = decide_skill(req.message)
        ctx = TurnContext(request=req)

        # Use the existing ConciergeCrew runtime, but enrich the result.
        result = self.orchestrator.run(req)

        # Keep ConciergeFlow's parsed intent; Hermes skill is internal routing only.
        # Ensure per-turn context sources/actions are surfaced.
        result.sources = ctx.retrieved_sources
        result.proposed_actions = ctx.proposed_actions

        return result

    def greet(self, guest_name: str | None = None) -> str:
        """Return a warm Hermes greeting for BAIA."""
        return self.persona.greeting(guest_name)
