"""Hermes' skill functions.

These are explicit, testable functions that decide how Hermes handles a guest.
They are derived from the 6 Hermes skill files in services/agent-api/skills/.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Skill = Literal[
    "verified_answer",
    "booking_inquiry",
    "hospitality_greeting",
    "local_recommendation",
    "complaint_escalation",
    "service_request",
    "unknown",
]


@dataclass(frozen=True)
class SkillDecision:
    skill: Skill
    requires_approval: bool = False
    escalation_reason: str | None = None
    note_for_model: str = ""


GREETING_KEYWORDS = ("hello", "hi", "hey", "good morning", "good afternoon", "good evening", "thank", "thanks")
BOOKING_KEYWORDS = ("book", "booking", "reservation", "reserve", "available", "availability", "room rate")
LOCAL_KEYWORDS = ("restaurant", "food", "beach", "tour", "activity", "nearby", "where to", "recommend")
SERVICE_KEYWORDS = ("towel", "toiletries", "wifi", "breakfast", "housekeeping", "clean", "extra", "request")
COMPLAINT_KEYWORDS = ("complaint", "angry", "unhappy", "disappointed", "problem", "issue", "bad", "terrible", "emergency")
CANCEL_KEYWORDS = ("cancel", "refund", "change dates")


def decide_skill(guest_message: str) -> SkillDecision:
    """Classify the guest's intent into a Hermes skill."""
    low = guest_message.lower()

    if any(k in low for k in COMPLAINT_KEYWORDS):
        return SkillDecision(
            skill="complaint_escalation",
            requires_approval=True,
            escalation_reason="topic_requires_human:complaint",
            note_for_model=(
                "This guest sounds upset or is reporting a serious issue. "
                "Be calm, apologize if appropriate, and explain you will bring this "
                "to the BAIA team immediately. Do not try to solve it yourself."
            ),
        )

    if any(k in low for k in CANCEL_KEYWORDS):
        return SkillDecision(
            skill="booking_inquiry",
            requires_approval=True,
            escalation_reason="topic_requires_human:booking_modification",
            note_for_model=(
                "This is a booking modification request. Collect relevant details "
                "but do not confirm or process any change; escalate to the BAIA team."
            ),
        )

    if any(k in low for k in BOOKING_KEYWORDS):
        return SkillDecision(
            skill="booking_inquiry",
            note_for_model=(
                "Help with BAIA room types, rates, and policies. Do NOT confirm, hold, "
                "or guarantee a booking. Direct the guest to the booking team or website."
            ),
        )

    if any(k in low for k in LOCAL_KEYWORDS):
        return SkillDecision(
            skill="local_recommendation",
            note_for_model=(
                "Recommend only verified local spots in San Vicente that BAIA has shared. "
                "Do not promise availability, hours, or prices for third parties."
            ),
        )

    if any(k in low for k in SERVICE_KEYWORDS):
        return SkillDecision(
            skill="service_request",
            requires_approval=True,
            escalation_reason="topic_requires_human:service_request",
            note_for_model=(
                "Capture the service request clearly, confirm understanding, "
                "and say you will pass it to the BAIA team. Do not promise timing."
            ),
        )

    if any(k in low for k in GREETING_KEYWORDS):
        return SkillDecision(skill="hospitality_greeting")

    return SkillDecision(skill="verified_answer")


def apply_skill_to_system_prompt(base_prompt: str, decision: SkillDecision) -> str:
    """Append the active skill instruction to the CrewAI system prompt."""
    if not decision.note_for_model:
        return base_prompt
    return f"{base_prompt}\n\n[active skill: {decision.skill}]\n{decision.note_for_model}"
