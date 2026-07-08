"""CrewAI Flow orchestrating the guest concierge pipeline.

The Flow is the controlled orchestration layer around the EXISTING
:class:`ConciergeCrew` (which it reuses, never replaces):

    credentials check → tenant resolution (fail closed) → CrewAI execution
    → safety validation → structured result

FastAPI calls this Flow via ``run_concierge`` in
``app.services.concierge_service``; nothing else executes the crew directly.
Sensitive values (the resolved OpenRouter key, the verified tenant context)
live on the Flow instance, never inside the serializable state.
"""

from __future__ import annotations

import re

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel

from app.agents.safety import detect_escalation, detect_forbidden
from app.crews.concierge.crew import ConciergeCrew, TenantKnowledgeTool
from app.knowledge.embeddings import get_embedding_provider
from app.knowledge.qdrant_store import TenantQdrantStore
from app.knowledge.repository import KnowledgeRepository
from app.security.secrets import safe_log
from app.services.credentials import get_credentials_provider
from app.services.tenant_resolver import (
    TenantContext,
    TenantResolutionError,
    TenantResolver,
)


class OpenRouterNotConfigured(RuntimeError):
    """Raised when no OpenRouter key is available for the requested resort."""


class TenantNotResolvable(RuntimeError):
    """Raised when a tenant cannot be resolved or is not permitted."""


def parse_intent_confidence(text: str) -> tuple[str, float]:
    """Lightweight parse of the CrewAI reply for intent + confidence.

    The real LLM is expected to include these; we extract defensively so the
    structured contract is always populated even if the model is terse.
    """
    intent = "general_inquiry"
    confidence = 0.6
    m = re.search(r"intent[:\s]+([a-z_]{2,30})", text, re.IGNORECASE)
    if m:
        intent = m.group(1).strip().lower().replace(" ", "_")[:40]
    m = re.search(r"confidence[:\s]+([01](?:\.\d+)?)", text, re.IGNORECASE)
    if m:
        try:
            confidence = max(0.0, min(1.0, float(m.group(1))))
        except ValueError:
            pass
    return intent, confidence


class ConciergeFlowState(BaseModel):
    """Serializable flow state. Never carries secrets or raw tenant rows.

    ``conversation_id`` is carried through untouched so the caller's thread
    identity survives the flow — no fabricated memory is attached to it.
    """

    resort_id: str = ""
    conversation_id: str = ""
    message: str = ""
    locale: str = "en"

    reply: str = ""
    intent: str = "general_inquiry"
    confidence: float = 0.6
    requires_approval: bool = False
    escalation_reason: str | None = None


class ConciergeFlow(Flow[ConciergeFlowState]):
    """Controlled concierge pipeline around the existing ConciergeCrew."""

    # Non-serializable, sensitive runtime objects (instance-only, not state).
    _api_key: str = ""
    _ctx: TenantContext | None = None

    @start()
    def gate_credentials_and_tenant(self) -> None:
        """Fail closed before any retrieval or LLM work."""
        creds = get_credentials_provider()
        api_key = creds.get_openrouter_key(self.state.resort_id)
        if not api_key:
            safe_log(f"OpenRouter not configured for resort {self.state.resort_id}")
            raise OpenRouterNotConfigured(
                "OpenRouter is not configured for this resort. The owner must "
                "connect their own OpenRouter key."
            )
        self._api_key = api_key

        repo = KnowledgeRepository()
        resolver = TenantResolver(lookup=repo.get_tenant_by_slug)
        try:
            self._ctx = resolver.resolve_by_slug(self.state.resort_id)
        except TenantResolutionError as exc:
            raise TenantNotResolvable(str(exc)) from exc

    @listen(gate_credentials_and_tenant)
    def run_crew(self) -> None:
        """Execute the EXISTING ConciergeCrew for the verified tenant."""
        ctx = self._ctx
        assert ctx is not None  # guaranteed by the gate step
        # Real embedding provider only; raises EmbeddingNotConfigured.
        embedder = get_embedding_provider()
        store = TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)
        tool = TenantKnowledgeTool(ctx, embedder, store)
        crew = ConciergeCrew(
            ctx,
            knowledge_tool=tool,
            embedder=embedder,
            openrouter_api_key=self._api_key,
        ).build()
        safe_log(
            f"Concierge request tenant={ctx.tenant_slug} id={ctx.tenant_id} "
            f"conversation={self.state.conversation_id}"
        )
        result = crew.kickoff(inputs={"guest_message": self.state.message})
        self.state.reply = (getattr(result, "raw", None) or str(result)).strip()

    @listen(run_crew)
    def validate_safety(self) -> None:
        """Safety checks over guest message + reply; sets escalation flags."""
        intent, confidence = parse_intent_confidence(self.state.reply)
        self.state.intent = intent
        self.state.confidence = confidence

        forbidden = detect_forbidden(self.state.message, self.state.reply)
        escalation = detect_escalation(self.state.message)
        self.state.requires_approval = bool(forbidden) or escalation is not None
        if forbidden:
            self.state.escalation_reason = f"forbidden_action:{','.join(forbidden)}"
        elif escalation:
            self.state.escalation_reason = escalation
        else:
            self.state.escalation_reason = None
