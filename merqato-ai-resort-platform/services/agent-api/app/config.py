from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Canonical tenant slug for the BAIA resort. The same value is used by the
# Next.js BFF (src/lib/config.ts), Supabase seeds, and Qdrant collection
# naming. Keep in sync — never scatter tenant-slug literals.
DEFAULT_TENANT_SLUG = "baia-resort"


class Settings(BaseSettings):
    """Server configuration. Loaded from environment / .env only.

    No secrets are ever hardcoded. Secrets (OpenRouter, OpenAI, Supabase
    service role, Qdrant) are read from the environment and accessible only
    inside the FastAPI process. They are never logged, never returned in API
    responses, and never committed.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # OpenRouter (each resort will later supply its own key via CredentialsProvider)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"

    # Supabase (multi-tenant source of truth; accessed via service-role key)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Qdrant (per-tenant vector storage/retrieval)
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # Knowledge embeddings
    knowledge_embedding_provider: str = "openai"  # openai | none
    knowledge_embedding_model: str = "text-embedding-3-small"
    # Required only when the OpenAI embedding provider is configured.
    openai_api_key: str = ""

    # Admin knowledge API (server-to-server). The Next.js BFF sends this
    # shared secret in X-Admin-Token; browsers never see it. When unset, the
    # admin knowledge routes fail closed (503).
    admin_api_token: str = ""

    # Service
    service_name: str = "merqato-agent-api"
    log_level: str = "INFO"

    @property
    def embedding_dimension(self) -> int:
        """Vector size must be explicit per provider/model — never guessed.

        text-embedding-3-small produces 1536-dim vectors.
        """
        if self.knowledge_embedding_provider == "openai":
            if self.knowledge_embedding_model == "text-embedding-3-small":
                return 1536
            if self.knowledge_embedding_model == "text-embedding-3-large":
                return 3072
            if self.knowledge_embedding_model == "text-embedding-ada-002":
                return 1536
        return 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
