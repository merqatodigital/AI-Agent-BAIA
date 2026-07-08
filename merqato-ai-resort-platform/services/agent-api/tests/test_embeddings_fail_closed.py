"""Production embedding selection must fail closed — never a fake provider."""

from __future__ import annotations

import pytest

from app.knowledge.embeddings import (
    EmbeddingNotConfigured,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)


def test_missing_openai_key_fails_closed(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(EmbeddingNotConfigured):
        get_embedding_provider()


def test_unsupported_provider_fails_closed(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDING_PROVIDER", "none")
    with pytest.raises(EmbeddingNotConfigured):
        get_embedding_provider()


def test_configured_openai_provider_is_returned(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_EMBEDDING_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-embedding-key")
    provider = get_embedding_provider()
    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.dimension == 1536


def test_concierge_route_fails_closed_without_embeddings(
    baia_tenant, client, monkeypatch
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-real")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post(
        "/v1/concierge/message",
        json={
            "resort_id": baia_tenant,
            "conversation_id": "c1",
            "message": "Hello",
            "locale": "en",
        },
    )
    assert r.status_code == 503
    assert "embedding" in r.json()["detail"].lower()
