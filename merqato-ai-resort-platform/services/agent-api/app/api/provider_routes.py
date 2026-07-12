from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.knowledge_routes import require_admin_token
from app.config import get_settings

router = APIRouter(
    prefix="/v1/admin/tenants/{slug}/ai-provider",
    dependencies=[Depends(require_admin_token)],
)

RuntimeMode = Literal["openrouter", "ollama", "hermes"]
HermesProvider = Literal["openrouter", "ollama"]


class ProviderSettingsIn(BaseModel):
    mode: RuntimeMode = "openrouter"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    hermes_provider: HermesProvider = "openrouter"


class ProviderSettingsOut(BaseModel):
    mode: RuntimeMode
    openrouter_configured: bool
    openrouter_key_masked: str | None = None
    openrouter_model: str
    ollama_base_url: str
    ollama_model: str
    hermes_provider: HermesProvider


class OllamaDetectRequest(BaseModel):
    base_url: str = Field(default="http://localhost:11434", min_length=8)


class OllamaDetectResponse(BaseModel):
    available: bool
    models: list[str] = Field(default_factory=list)
    message: str


class OpenRouterModelsRequest(BaseModel):
    api_key: str | None = None


class OpenRouterModel(BaseModel):
    id: str
    name: str
    is_free: bool = False
    context_length: int | None = None


class OpenRouterModelsResponse(BaseModel):
    models: list[OpenRouterModel] = Field(default_factory=list)


def _store_path() -> Path:
    configured = os.getenv("PROVIDER_SETTINGS_PATH", ".data/provider-settings.json")
    path = Path(configured)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fernet() -> Fernet:
    key = os.getenv("PROVIDER_SETTINGS_ENCRYPTION_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="provider settings encryption is not configured")
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="provider settings encryption key is invalid") from exc


def _load_all() -> dict[str, dict[str, object]]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="provider settings store is unreadable") from exc


def _save_all(data: dict[str, dict[str, object]]) -> None:
    path = _store_path()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    suffix = key[-4:] if len(key) >= 4 else key
    return f"••••••••{suffix}"


def _decrypt_key(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="saved provider credentials cannot be decrypted") from exc


def _to_output(raw: dict[str, object]) -> ProviderSettingsOut:
    key = _decrypt_key(raw.get("openrouter_api_key_encrypted"))
    return ProviderSettingsOut(
        mode=str(raw.get("mode", "openrouter")),
        openrouter_configured=bool(key),
        openrouter_key_masked=_mask_key(key),
        openrouter_model=str(raw.get("openrouter_model", "openai/gpt-4o-mini")),
        ollama_base_url=str(raw.get("ollama_base_url", "http://localhost:11434")),
        ollama_model=str(raw.get("ollama_model", "qwen2.5:3b")),
        hermes_provider=str(raw.get("hermes_provider", "openrouter")),
    )


def _saved_openrouter_key(slug: str) -> str | None:
    raw = _load_all().get(slug, {})
    return _decrypt_key(raw.get("openrouter_api_key_encrypted"))


@router.get("", response_model=ProviderSettingsOut)
def get_provider_settings(slug: str) -> ProviderSettingsOut:
    data = _load_all()
    raw = data.get(slug, {})
    if not raw:
        settings = get_settings()
        raw = {
            "mode": "openrouter",
            "openrouter_model": settings.openrouter_model,
            "ollama_base_url": settings.ollama_base_url,
            "ollama_model": settings.ollama_model,
            "hermes_provider": "openrouter",
        }
    return _to_output(raw)


@router.put("", response_model=ProviderSettingsOut)
def save_provider_settings(slug: str, body: ProviderSettingsIn) -> ProviderSettingsOut:
    data = _load_all()
    previous = data.get(slug, {})
    encrypted_key = previous.get("openrouter_api_key_encrypted")
    if body.openrouter_api_key:
        encrypted_key = _fernet().encrypt(body.openrouter_api_key.encode("utf-8")).decode("utf-8")

    raw: dict[str, object] = {
        "mode": body.mode,
        "openrouter_api_key_encrypted": encrypted_key or "",
        "openrouter_model": body.openrouter_model,
        "ollama_base_url": body.ollama_base_url.rstrip("/"),
        "ollama_model": body.ollama_model,
        "hermes_provider": body.hermes_provider,
    }
    data[slug] = raw
    _save_all(data)
    return _to_output(raw)


@router.delete("/openrouter-key", response_model=ProviderSettingsOut)
def delete_openrouter_key(slug: str) -> ProviderSettingsOut:
    data = _load_all()
    raw = data.get(slug, {})
    raw["openrouter_api_key_encrypted"] = ""
    data[slug] = raw
    _save_all(data)
    return _to_output(raw)


@router.post("/openrouter/models", response_model=OpenRouterModelsResponse)
def list_openrouter_models(slug: str, body: OpenRouterModelsRequest) -> OpenRouterModelsResponse:
    api_key = (body.api_key or "").strip() or _saved_openrouter_key(slug)
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenRouter API key required")

    request = Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed OpenRouter endpoint
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(status_code=400, detail="OpenRouter rejected the API key") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Unable to load OpenRouter models") from exc

    models: list[OpenRouterModel] = []
    for item in payload.get("data", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
        prompt_price = str(pricing.get("prompt", ""))
        completion_price = str(pricing.get("completion", ""))
        is_free = prompt_price in {"0", "0.0", "0.000000"} and completion_price in {"0", "0.0", "0.000000"}
        models.append(
            OpenRouterModel(
                id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                is_free=is_free,
                context_length=item.get("context_length") if isinstance(item.get("context_length"), int) else None,
            )
        )
    models.sort(key=lambda model: (not model.is_free, model.name.lower()))
    return OpenRouterModelsResponse(models=models)


@router.post("/ollama/detect", response_model=OllamaDetectResponse)
def detect_ollama(slug: str, body: OllamaDetectRequest) -> OllamaDetectResponse:
    del slug
    base_url = body.base_url.rstrip("/")
    request = Request(f"{base_url}/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=3) as response:  # noqa: S310 - admin-configured local endpoint
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        return OllamaDetectResponse(
            available=False,
            models=[],
            message=f"Ollama was not detected at {base_url}.",
        )

    models = sorted(
        str(item.get("name"))
        for item in payload.get("models", [])
        if isinstance(item, dict) and item.get("name")
    )
    return OllamaDetectResponse(
        available=True,
        models=models,
        message="Ollama is available." if models else "Ollama is available but no models are installed.",
    )
