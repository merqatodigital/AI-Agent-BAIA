from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.config import get_settings


class EmbeddingNotConfigured(RuntimeError):
    """Raised when no usable production embedding provider is configured.

    Production code must fail closed instead of silently substituting a fake
    provider.
    """


class EmbeddingProvider(ABC):
    """Typed embedding abstraction. No dependency on CrewAI execution."""

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings. Requires OPENAI_API_KEY when provider is 'openai'.

    The client is imported lazily so unit tests can use a test double.
    """

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self._settings = get_settings()
        self._model = model or self._settings.knowledge_embedding_model
        self._api_key = api_key if api_key is not None else self._settings.openai_api_key
        self._client: Any = None

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._settings.embedding_dimension

    def _get_client(self) -> Any:
        if self._client is None:
            try:  # pragma: no cover - only with openai installed
                from openai import OpenAI

                self._client = OpenAI(api_key=self._api_key or None)
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(f"OpenAI client unavailable: {exc}") from exc
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._get_client().embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]


class FastEmbedProvider(EmbeddingProvider):
    """Local, key-free embeddings via fastembed (BAAI/bge-small-en-v1.5).

    Runs entirely on this host — no external API, no secret. Suitable for
    production when an external embedding provider (OpenAI) is unavailable.
    The model is loaded lazily so import/unit tests stay cheap.
    """

    _DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
    _DEFAULT_DIM = 384

    def __init__(self, model: str | None = None, dimension: int | None = None) -> None:
        self._model_name = model or self._DEFAULT_MODEL
        self._dim = dimension or self._DEFAULT_DIM
        self._model: Any = None

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dim

    def _get_model(self) -> Any:
        if self._model is None:
            try:  # pragma: no cover - needs the optional fastembed dep
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self._model_name)
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(f"fastembed unavailable: {exc}") from exc
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(vec) for vec in self._get_model().embed(texts)]


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic test double. Hashes text into a stable fixed-dim vector.

    NOT for production — used only in unit tests.
    """

    def __init__(self, dimension: int = 1536, model: str = "fake-embed") -> None:
        self._dim = dimension
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            vec = [0.0] * self._dim
            for i, ch in enumerate(t):
                idx = i % self._dim
                vec[idx] += float(ord(ch)) / 1000.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


def get_embedding_provider() -> EmbeddingProvider:
    """Factory: returns the configured production provider, failing closed.

    Raises :class:`EmbeddingNotConfigured` when the provider selection or its
    credentials are missing. Never returns :class:`FakeEmbeddingProvider`.
    """
    settings = get_settings()
    if settings.knowledge_embedding_provider == "openai":
        if not settings.openai_api_key:
            raise EmbeddingNotConfigured(
                "embedding provider 'openai' selected but OPENAI_API_KEY is not set"
            )
        return OpenAIEmbeddingProvider()
    if settings.knowledge_embedding_provider == "fastembed":
        # Local, key-free. Requires the optional 'fastembed' dependency.
        return FastEmbedProvider(
            model=settings.knowledge_embedding_model or None,
            dimension=settings.embedding_dimension or None,
        )
    raise EmbeddingNotConfigured(
        f"unsupported embedding provider: {settings.knowledge_embedding_provider!r}"
    )
