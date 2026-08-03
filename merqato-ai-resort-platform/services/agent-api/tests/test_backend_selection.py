"""Runtime knowledge-backend selection.

Supabase (service role) must be the default backend whenever the Supabase
env vars are configured; the in-memory backend remains only for tests and
zero-config local runs.
"""

from __future__ import annotations

from app.config import get_settings
from app.knowledge.repository import KnowledgeRepository, _InMemoryBackend
from app.knowledge.supabase_backend import SupabaseBackend


def test_default_backend_is_in_memory_without_supabase_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    repo = KnowledgeRepository()
    assert isinstance(repo._backend, _InMemoryBackend)


def test_default_backend_is_supabase_with_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    get_settings.cache_clear()
    repo = KnowledgeRepository()
    assert isinstance(repo._backend, SupabaseBackend)


def test_partial_supabase_env_falls_back_to_memory(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    get_settings.cache_clear()
    repo = KnowledgeRepository()
    assert isinstance(repo._backend, _InMemoryBackend)


def test_explicit_backend_wins_over_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
    mem = _InMemoryBackend()
    repo = KnowledgeRepository(backend=mem)
    assert repo._backend is mem
