"""Per-turn memory for Hermes.

Hermes intentionally does NOT persist conversation history server-side.
The caller owns long-term memory via conversation_id. This module only
provides a clean in-turn context object for the current request.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.schemas import ConciergeRequest


@dataclass
class TurnContext:
    """Lightweight request context for one guest turn."""

    request: ConciergeRequest
    retrieved_sources: list[str] = field(default_factory=list)
    proposed_actions: list[str] = field(default_factory=list)

    @property
    def resort_id(self) -> str:
        return self.request.resort_id

    @property
    def guest_message(self) -> str:
        return self.request.message

    @property
    def locale(self) -> str:
        return self.request.locale

    @property
    def conversation_id(self) -> str:
        return self.request.conversation_id
