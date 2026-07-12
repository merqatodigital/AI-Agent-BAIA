from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal
from urllib.error import URLError
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

ProviderMode = Literal["automatic", "openrouter", "ollama"]


class ProviderSettingsIn(BaseModel):
    mode: ProviderMode = "automatic"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    allow_fallback: bool = False


class ProviderSettingsOut(BaseModel):
    mode: ProviderMode
    openrouter_configured: bool
    openrouter_key_masked: str | None = None
    openrouter_model: str
    ollama_base_url: str
    ollama_model: str
    allow_fallback: bool


class OllamaDetectRequest(BaseModel):
    base_url: str = Field(default="http://localhost:11434", min_length=8)


class OllamaDetectResponse(BaseModel):
    available: bool
    models: list[str] = Field(default_factory=list)
    message: str


def _store_path() -> Path:
    configured = os.getenv("PROVIDER_SETTINGS_PATH", ".data/provider-settings.json")
    path = Path(configured)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _fernet() -> Fernet:
    key = os.getenv("PROVIDER_SETTINGS_ENCRYPTION_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="provider settings encryption is not configured",
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="provider settings encryption key is invalid",
        ) from exc


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
        mode=str(raw.get("mode", "automatic")),
        openrouter_configured=bool(key),
        openrouter_key_masked=_mask_key(key),
        openrouter_model=str(raw.get("openrouter_model", "openai/gpt-4o-mini")),
        ollama_base_url=str(raw.get("ollama_base_url", "http://localhost:11434")),
        ollama_model=str(raw.get("ollama_model", "qwen2.5:3b")),
        allow_fallback=bool(raw.get("allow_fallback", False)),
    )


@router.get("", response_model=ProviderSettingsOut)
def get_provider_settings(slug: str) -> ProviderSettingsOut:
    data = _load_all()
    raw = data.get(slug, {})
    if not raw:
        settings = get_settings()
        raw = {
            "mode": "automatic",
            "openrouter_model": settings.openrouter_model,
            "ollama_base_url": settings.ollama_base_url,
            "ollama_model": settings.ollama_model,
            "allow_fallback": False,
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
        "allow_fallback": body.allow_fallback,
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


@router.post("/ollama/detect", response_model=OllamaDetectResponse)
def detect_ollama(slug: str, body: OllamaDetectRequest) -> OllamaDetectResponse:
    del slug
    base_url = body.base_url.rstrip("/")
    request = Request(f"{base_url}/api/tags", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=3) as response:  # noqa: S310 - admin-configured local endpoint
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
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
