from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from app.config import get_settings

# Prefix for all tenant collections. Never derive a collection name from any
# client-supplied value; always use tenant_collection_name().
COLLECTION_PREFIX = "merqato_tenant_"

_SLUG_SAFE = re.compile(r"[^a-z0-9_]")


def normalize_slug(slug: str) -> str:
    """Normalize a tenant slug to lowercase safe characters.

    Lowercase only, underscores/letters/digits kept, everything else becomes
    underscore. Result is deterministic.
    """
    return _SLUG_SAFE.sub("_", slug.strip().lower())


def tenant_collection_name(slug: str) -> str:
    """Server-generated, deterministic Qdrant collection name for a tenant.

    Rules:
      - lowercase only
      - safe characters only (a-z0-9_)
      - deterministic
      - rejects empty/invalid slugs
      - never accepts an arbitrary client-supplied collection name

    Example: "baia_resort" -> "merqato_tenant_baia_resort"
    """
    if not slug or not isinstance(slug, str):
        raise ValueError("tenant slug is required for collection naming")
    norm = normalize_slug(slug)
    if not norm:
        raise ValueError("tenant slug normalizes to an empty collection name")
    return f"{COLLECTION_PREFIX}{norm}"


@runtime_checkable
class VectorClient(Protocol):
    """Minimal transport surface used by QdrantStore (duck-typed for tests)."""

    def collection_exists(self, collection_name: str) -> bool: ...

    def get_collection(self, collection_name: str) -> Any: ...

    def create_collection(
        self,
        collection_name: str,
        vectors_config: Any,
    ) -> Any: ...

    def upsert(self, collection_name: str, points: Any) -> Any: ...

    def delete(
        self,
        collection_name: str,
        points_selector: Any,
    ) -> Any: ...

    def query_points(
        self,
        collection_name: str,
        query: list[float],
        limit: int,
        with_payload: bool,
        query_filter: Any | None = None,
    ) -> Any: ...


class CollectionConfigError(ValueError):
    """Raised when an existing Qdrant collection is incompatible (e.g. dimension)."""

    def __init__(self, message: str, *, expected: int | None = None) -> None:
        super().__init__(message)
        self.expected_dimension = expected


@dataclass(frozen=True)
class CollectionConfig:
    """Resolved collection configuration (returned by ensure_collection)."""

    name: str
    dimension: int
    distance: str


class TenantQdrantStore:
    """Per-tenant Qdrant storage/retrieval. One collection per tenant.

    The collection name is ALWAYS derived from the verified tenant slug via
    tenant_collection_name(); an arbitrary client-supplied collection name is
    never accepted. No cross-tenant search method exists.
    """

    def __init__(
        self,
        tenant_id: str,
        tenant_slug: str,
        *,  # keyword-only
        client: VectorClient | None = None,
        dimension: int | None = None,
        distance: str = "cosine",
    ) -> None:
        if not tenant_id or not tenant_slug:
            raise ValueError("tenant_id and tenant_slug are required")
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.collection_name = tenant_collection_name(tenant_slug)
        self._settings = get_settings()
        self._dimension = dimension or self._settings.embedding_dimension
        self._distance = distance.lower()
        self._client = client

    # --- low-level helpers ------------------------------------------------
    def _require_client(self) -> VectorClient:
        if self._client is None:
            self._client = self._real_client()
        return self._client

    def _real_client(self) -> Any:
        # Lazily import the real client only when a live connection is needed.
        try:  # pragma: no cover - exercised only with qdrant-client installed
            from qdrant_client import QdrantClient

            return QdrantClient(
                url=self._settings.qdrant_url,
                api_key=self._settings.qdrant_api_key or None,
            )
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Qdrant client unavailable: {exc}") from exc

    def _vectors_config(self) -> Any:
        if self._dimension <= 0:
            raise CollectionConfigError(
                "embedding dimension is unknown; configure an embedding provider"
            )
        from qdrant_client.models import Distance, VectorParams

        dist = Distance.COSINE if self._distance == "cosine" else Distance.EUCLID
        return VectorParams(size=self._dimension, distance=dist)

    # --- collection management ------------------------------------------- #
    def ensure_collection(self) -> CollectionConfig:
        """Create the tenant collection if absent; verify config if present.

        Returns the resolved CollectionConfig. Fails safely when an existing
        collection's vector dimension is incompatible.
        """
        client = self._require_client()
        if client.collection_exists(self.collection_name):
            self._verify_compatible(client)
        else:
            client.create_collection(self.collection_name, self._vectors_config())
        return CollectionConfig(
            name=self.collection_name,
            dimension=self._dimension,
            distance=self._distance,
        )

    def _verify_compatible(self, client: VectorClient) -> None:
        info = client.get_collection(self.collection_name)
        # qdrant_client returns a models.CollectionInfo with .config.params.vectors
        vectors = getattr(info, "config", None)
        params = getattr(vectors, "params", None)
        vecs = getattr(params, "vectors", None)
        size = getattr(vecs, "size", None)
        if size is not None and self._dimension > 0 and size != self._dimension:
            raise CollectionConfigError(
                f"collection {self.collection_name} has dimension {size}, "
                f"expected {self._dimension}",
                expected=self._dimension,
            )

    # --- writes -----------------------------------------------------------
    def upsert_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Upsert embedded chunks. Each chunk must carry a complete payload."""
        if not chunks:
            return 0
        self.ensure_collection()
        client = self._require_client()
        points = []
        for c in chunks:
            payload = c.get("payload", {})
            points.append(
                {
                    "id": c["id"],
                    "vector": c["vector"],
                    "payload": payload,
                }
            )
        client.upsert(self.collection_name, points)
        return len(points)

    def delete_document_vectors(self, document_id: str) -> None:
        """Delete all vectors for a superseded document version."""
        client = self._require_client()
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client.delete(
            self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id", match=MatchValue(value=document_id)
                    )
                ]
            ),
        )

    # --- reads -------------------------------------------------------------
    def search(
        self,
        query_vector: list[float],
        *,
        limit: int = 5,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Tenant-specific semantic search. No cross-tenant scope possible."""
        client = self._require_client()
        from qdrant_client.models import (
            FieldCondition,
            MatchValue,
        )
        from qdrant_client.models import (
            Filter as QFilter,
        )

        # Restrict to this tenant by construction (collection is per-tenant),
        # but also assert tenant_id in payload for defense-in-depth.
        filt = QFilter(
            must=[
                FieldCondition(key="tenant_id", match=MatchValue(value=self.tenant_id)),
                FieldCondition(key="guest_visible", match=MatchValue(value=True)),
                FieldCondition(key="internal_only", match=MatchValue(value=False)),
            ]
        )
        resp = client.query_points(
            self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            query_filter=filt,
        )
        out: list[dict[str, Any]] = []
        for pt in getattr(resp, "points", []) or []:
            out.append(
                {
                    "id": getattr(pt, "id", None),
                    "score": getattr(pt, "score", 0.0),
                    "payload": getattr(pt, "payload", {}) or {},
                }
            )
        return out
