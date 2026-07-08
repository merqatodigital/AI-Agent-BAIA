from __future__ import annotations

# Consequential actions the agent may NEVER perform autonomously.
# Any detected intent sets requires_approval=True and an escalation reason.
FORBIDDEN_ACTIONS: list[tuple[str, str]] = [
    ("confirm a booking", "booking_confirmation"),
    ("confirm booking", "booking_confirmation"),
    ("confirmed booking", "booking_confirmation"),
    ("confirm my booking", "booking_confirmation"),
    ("cancel a booking", "booking_cancellation"),
    ("cancel booking", "booking_cancellation"),
    ("cancel my booking", "booking_cancellation"),
    ("cancelled booking", "booking_cancellation"),
    ("issue a refund", "refund"),
    ("issue refund", "refund"),
    ("refund my", "refund"),
    ("charge", "payment"),
    ("charge money", "payment"),
    ("change price", "price_change"),
    ("change the price", "price_change"),
    ("publish", "publish_content"),
    ("delete", "delete_record"),
    ("send an email", "external_message"),
    ("send a message", "external_message"),
    ("email the guest", "external_message"),
    ("promise a tour", "availability_promise"),
    ("promise transport", "availability_promise"),
    ("promise availability", "availability_promise"),
    ("guarantee availability", "availability_promise"),
]

# Topics that must always escalate to a human.
ESCALATION_TOPICS = ["complaint", "emergency", "refund", "cancel", "cancellation"]


def detect_forbidden(message: str, reply: str = "") -> list[str]:
    """Returns the list of forbidden-action codes found in the text."""
    text = f"{message} {reply}".lower()
    hits: list[str] = []
    for phrase, code in FORBIDDEN_ACTIONS:
        if phrase in text:
            hits.append(code)
    return hits


def detect_escalation(message: str) -> str | None:
    low = message.lower()
    for topic in ESCALATION_TOPICS:
        if topic in low:
            return f"topic_requires_human:{topic}"
    return None
