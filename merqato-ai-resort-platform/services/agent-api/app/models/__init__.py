from __future__ import annotations

import importlib.metadata

__all__ = ["get_crewai_version"]


def get_crewai_version() -> str:
    """Reads the real, installed CrewAI version from package metadata."""
    try:
        return importlib.metadata.version("crewai")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "unknown"
