from __future__ import annotations

# app.agents now hosts only safety logic. Concierge crew construction lives in
# app.crews.concierge (YAML + CrewBase structure).
from .safety import detect_escalation, detect_forbidden

__all__ = ["detect_escalation", "detect_forbidden"]
