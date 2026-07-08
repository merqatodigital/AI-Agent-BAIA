from __future__ import annotations

import json
from typing import Any

# Deterministic ordering keeps checksums stable across runs.
_INDENT = 2


def _sort_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sort_keys(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort_keys(v) for v in obj]
    return obj


def canonical_json(content: dict[str, Any]) -> str:
    """Canonical, stable JSON string (sorted keys) for checksumming."""
    return json.dumps(_sort_keys(content), ensure_ascii=False, sort_keys=True)


def _format_scalar(key: str, value: Any) -> str:
    if value is None:
        return f"{key}: (not specified)"
    if isinstance(value, bool):
        return f"{key}: {'yes' if value else 'no'}"
    return f"{key}: {value}"


def _format_value(key: str, value: Any, *, indent: int = 0) -> list[str]:
    """Format a single key/value pair into stable lines.

    Mirrors nested meaning without injecting behavior or invented prose.
    """
    pad = "  " * indent
    if isinstance(value, dict):
        lines = [f"{pad}{key}:"]
        for k in sorted(value.keys()):
            lines.extend(_format_value(k, value[k], indent=indent + 1))
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{pad}{key}: (none)"]
        lines = [f"{pad}{key}:"]
        for item in value:
            if isinstance(item, dict):
                sub = [
                    "  " + s.lstrip()
                    for s in _format_value("(item)", item, indent=indent + 1)
                ]
                lines.extend(sub)
            else:
                lines.append(f"{pad}  - {item}")
        return lines
    return [_format_scalar(key, value)]


def format_knowledge(category: str, content: dict[str, Any]) -> str:
    """Convert factual JSON into deterministic semantic text.

    Preserves field names/values and nested meaning. Does NOT inject behavioral
    instructions, tones, or invented descriptions. Stable ordering => stable
    checksums for unchanged content.
    """
    lines: list[str] = [f"Category: {category}"]
    for key in sorted(content.keys()):
        lines.extend(_format_value(key, content[key], indent=0))
    return "\n".join(lines)
