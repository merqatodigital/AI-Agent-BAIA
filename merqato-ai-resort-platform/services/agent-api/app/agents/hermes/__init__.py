"""Hermes: BAIA's guest-facing AI concierge.

Hermes is a thin, opinionated operator layer on top of the existing
CrewAI runtime (`app.crews.concierge`). It owns the BAIA persona,
skill boundaries, safety checks, and request/response shape, while the
ConciergeCrew handles the actual tool use and LLM calls.

Public API:
    from app.agents.hermes import Hermes
    response = await Hermes().assist(req)
"""

from __future__ import annotations

from app.agents.hermes.agent import Hermes

__all__ = ["Hermes"]
