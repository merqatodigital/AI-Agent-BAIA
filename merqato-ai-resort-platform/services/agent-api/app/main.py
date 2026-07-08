from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.models import get_crewai_version
from app.models.schemas import HealthResponse

app = FastAPI(title="MerQato Agent API")

app.include_router(router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        crewai_version=get_crewai_version(),
        environment=settings.environment,
        openrouter_configured=bool(settings.openrouter_api_key),
    )
