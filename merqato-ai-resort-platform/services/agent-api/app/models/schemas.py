from __future__ import annotations

from pydantic import BaseModel, Field


class ConciergeRequest(BaseModel):
    resort_id: str
    conversation_id: str
    message: str
    locale: str = "en"


class ConciergeResponse(BaseModel):
    reply: str
    intent: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)
    proposed_actions: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    escalation_reason: str | None = None
    # Echoed from the request untouched so the caller keeps its thread
    # identity. No server-side conversation memory is attached to it.
    conversation_id: str = ""


class HealthResponse(BaseModel):
    status: str
    crewai_version: str
    environment: str
    openrouter_configured: bool


class OpenRouterValidateRequest(BaseModel):
    api_key: str
    model: str | None = None


class OpenRouterValidateResponse(BaseModel):
    valid: bool
    model: str | None = None
    message: str
