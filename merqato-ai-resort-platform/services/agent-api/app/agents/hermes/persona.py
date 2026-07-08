"""Load Hermes' BAIA persona from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PERSONA_PATH = Path(__file__).with_name("persona.yaml")


def load_persona() -> dict[str, Any]:
    """Return the BAIA Hermes persona as a plain dict."""
    with _PERSONA_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class Persona:
    """Typed read-only access to the Hermes persona."""

    def __init__(self) -> None:
        self._data = load_persona()

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def title(self) -> str:
        return self._data["title"]

    @property
    def purpose(self) -> str:
        return self._data["purpose"].strip()

    @property
    def tone(self) -> list[str]:
        return list(self._data.get("tone", []))

    @property
    def identity_lines(self) -> list[str]:
        return list(self._data.get("identity", []))

    @property
    def boundaries(self) -> list[str]:
        return list(self._data.get("boundaries", []))

    @property
    def escalation_phrase(self) -> str:
        return self._data["escalation_phrase"].strip()

    def greeting(self, guest_name: str | None = None) -> str:
        """Return a warm BAIA greeting."""
        base = f"Hello{f', {guest_name}' if guest_name else ''}! I'm Hermes, your host at BAIA."
        return f"{base} How can I help make your stay in San Vicente wonderful?"
