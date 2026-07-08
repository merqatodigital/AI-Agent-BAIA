"""Filter-aware in-memory Qdrant test doubles.

Unlike the minimal fake in test_knowledge.py, these evaluate real
qdrant_client Filter/FieldCondition objects against point payloads, so the
guest-safety retrieval filters (verified/published/guest_visible/...) and the
document-scoped deletes are actually exercised.
"""

from __future__ import annotations

from typing import Any

from app.knowledge.qdrant_store import TenantQdrantStore


def _matches_filter(payload: dict[str, Any], query_filter: Any | None) -> bool:
    if query_filter is None:
        return True
    for cond in getattr(query_filter, "must", None) or []:
        key = getattr(cond, "key", None)
        match = getattr(cond, "match", None)
        expected = getattr(match, "value", None)
        if payload.get(key) != expected:
            return False
    return True


class _Point:
    def __init__(self, point: dict[str, Any]) -> None:
        self.id = point["id"]
        self.score = 1.0
        self.payload = point.get("payload", {})


class _QueryResponse:
    def __init__(self, points: list[dict[str, Any]]) -> None:
        self.points = [_Point(p) for p in points]


class FilterAwareVectorClient:
    """In-memory VectorClient that honours payload filters and deletes."""

    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension
        self.collections: dict[str, dict[str, dict[str, Any]]] = {}

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def get_collection(self, collection_name: str) -> Any:
        class _Info:
            config = None

        return _Info()

    def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.collections.setdefault(collection_name, {})

    def upsert(self, collection_name: str, points: Any) -> None:
        store = self.collections.setdefault(collection_name, {})
        for p in points:
            store[p["id"]] = p

    def delete(self, collection_name: str, points_selector: Any) -> None:
        store = self.collections.get(collection_name, {})
        doomed = [
            pid
            for pid, p in store.items()
            if _matches_filter(p.get("payload", {}), points_selector)
        ]
        for pid in doomed:
            del store[pid]

    def create_payload_index(
        self,
        collection_name: str,  # noqa: ARG002
        field_name: str,  # noqa: ARG002
        schema_type: Any,  # noqa: ARG002
    ) -> None:
        # In-memory double: indexing is a no-op (filters evaluated directly).
        return None

    def query_points(
        self,
        collection_name: str,
        query: list[float],  # noqa: ARG002 - similarity is irrelevant here
        limit: int,
        with_payload: bool,  # noqa: ARG002
        query_filter: Any | None = None,
    ) -> Any:
        store = self.collections.get(collection_name, {})
        hits = [
            p
            for p in store.values()
            if _matches_filter(p.get("payload", {}), query_filter)
        ]
        return _QueryResponse(hits[:limit])

    def all_points(self, collection_name: str) -> list[dict[str, Any]]:
        return list(self.collections.get(collection_name, {}).values())


def make_store(
    tenant_id: str,
    slug: str,
    *,
    client: FilterAwareVectorClient | None = None,
    dimension: int = 8,
) -> TenantQdrantStore:
    return TenantQdrantStore(
        tenant_id,
        slug,
        client=client or FilterAwareVectorClient(dimension=dimension),
        dimension=dimension,
    )
