"""Orchestrator: Hermes -> existing CrewAI Flow.

This module keeps Hermes decoupled from the ConciergeCrew internals.
It invokes the existing Flow and enriches the result with Hermes-level
metadata (skill classification, persona, sources).
"""

from __future__ import annotations

from app.agents.hermes.memory import TurnContext
from app.agents.hermes.persona import Persona
from app.agents.hermes.skills import SkillDecision, decide_skill
from app.crews.concierge.flow import (
    ConciergeFlow,
    OpenRouterNotConfigured,
    TenantNotResolvable,
)
from app.models.schemas import ConciergeRequest, ConciergeResponse


class HermesOrchestrator:
    """Run the CrewAI concierge Flow through Hermes' lens."""

    def __init__(self) -> None:
        self.persona = Persona()

    def run(self, req: ConciergeRequest) -> ConciergeResponse:
        """Execute one guest turn.

        Raises the same exceptions as the underlying Flow so the route layer
        can continue to fail closed in a controlled way.
        """
        decision = decide_skill(req.message)
        ctx = TurnContext(request=req)

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

        reply = self._post_process_reply(s.reply, decision, req)

        return ConciergeResponse(
            reply=reply,
            intent=s.intent,
            confidence=s.confidence,
            sources=ctx.retrieved_sources,
            proposed_actions=[],
            requires_approval=s.requires_approval or decision.requires_approval,
            escalation_reason=s.escalation_reason or decision.escalation_reason,
            conversation_id=s.conversation_id,
        )

    def _post_process_reply(
        self, raw_reply: str, decision: SkillDecision, req: ConciergeRequest
    ) -> str:
        """Apply Hermes-level polish without contradicting the crew's answer."""
        if decision.skill == "hospitality_greeting":
            # Ensure the first line is a warm Hermes greeting.
            return self.persona.greeting()
        if (decision.skill == "complaint_escalation" or decision.escalation_reason) and self.persona.escalation_phrase not in raw_reply:
            return f"{raw_reply.strip()}\n\n{self.persona.escalation_phrase}"
        return raw_reply.strip()
