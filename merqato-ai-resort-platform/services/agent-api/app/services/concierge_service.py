from __future__ import annotations

import re

from app.agents.safety import detect_escalation, detect_forbidden
from app.crews.concierge import ConciergeCrew
from app.crews.concierge.crew import TenantKnowledgeTool
from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.qdrant_store import TenantQdrantStore
from app.knowledge.repository import KnowledgeRepository
from app.models.schemas import ConciergeRequest, ConciergeResponse
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


def _parse_intent_confidence(text: str) -> tuple[str, float]:
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


def _resolve_tenant(resort_id: str) -> TenantContext:
    """Resolve a verified tenant from trusted server-side routing context.

    req.resort_id is treated as the tenant slug supplied by the trusted BFF
    (never a raw, unverified client id used to skip validation). The lookup is
    backed by the knowledge repository (Supabase in production, in-memory in dev).
    """
    repo = KnowledgeRepository()
    resolver = TenantResolver(lookup=repo.get_tenant_by_slug)
    try:
        return resolver.resolve_by_slug(resort_id)
    except TenantResolutionError as exc:
        raise TenantNotResolvable(str(exc)) from exc


def run_concierge(req: ConciergeRequest) -> ConciergeResponse:
    creds = get_credentials_provider()
    api_key = creds.get_openrouter_key(req.resort_id)

    if not api_key:
        safe_log(f"OpenRouter not configured for resort {req.resort_id}")
        raise OpenRouterNotConfigured(
            "OpenRouter is not configured for this resort. The owner must "
            "connect their own OpenRouter key."
        )

    # Verified tenant context is REQUIRED before any knowledge retrieval.
    ctx = _resolve_tenant(req.resort_id)

    embedder = FakeEmbeddingProvider()
    store = TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    tool = TenantKnowledgeTool(ctx, embedder, store)

    crew = ConciergeCrew(ctx, knowledge_tool=tool, embedder=embedder).build()
    safe_log(f"Concierge request tenant={ctx.tenant_slug} id={ctx.tenant_id}")
    # REAL CrewAI execution. Monkeypatchable in tests to avoid API credits.
    result = crew.kickoff(inputs={"guest_message": req.message})
    reply = getattr(result, "raw", None) or str(result)

    intent, confidence = _parse_intent_confidence(reply)

    forbidden = detect_forbidden(req.message, reply)
    escalation = detect_escalation(req.message)

    requires_approval = bool(forbidden) or escalation is not None
    escalation_reason = None
    if forbidden:
        escalation_reason = f"forbidden_action:{','.join(forbidden)}"
    elif escalation:
        escalation_reason = escalation

    return ConciergeResponse(
        reply=reply.strip(),
        intent=intent,
        confidence=confidence,
        sources=[],
        proposed_actions=[],
        requires_approval=requires_approval,
        escalation_reason=escalation_reason,
    )
