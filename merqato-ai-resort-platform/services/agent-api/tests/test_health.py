from __future__ import annotations

from app.models import get_crewai_version


def test_health_reports_real_crewai_version(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["crewai_version"] == get_crewai_version()
    # The installed version must be a real CrewAI release string.
    assert get_crewai_version() != "unknown"
