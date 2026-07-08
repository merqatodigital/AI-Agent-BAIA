from __future__ import annotations

from abc import ABC, abstractmethod

from app.config import get_settings


class CredentialsProvider(ABC):
    """Abstraction over per-resort secret storage.

    For this foundation milestone the implementation reads the customer key
    from the server environment. The production design will resolve a
    different encrypted key per resort_id without changing callers.
    """

    @abstractmethod
    def get_openrouter_key(self, resort_id: str) -> str:
        """Returns the OpenRouter API key for a resort. Never None/empty-safe."""
        raise NotImplementedError


class EnvCredentialsProvider(CredentialsProvider):
    """Reads OPENROUTER_API_KEY from the FastAPI server environment.

    The key is never sent to the browser and never written to logs or
    responses (see app.security.secrets).
    """

    def get_openrouter_key(self, resort_id: str) -> str:
        return get_settings().openrouter_api_key


_credentials: CredentialsProvider | None = None


def get_credentials_provider() -> CredentialsProvider:
    global _credentials
    if _credentials is None:
        _credentials = EnvCredentialsProvider()
    return _credentials
