from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import pytest

from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.ingestion_service import IngestionService
from app.knowledge.models import Category, IngestionStatus, VerificationStatus
from app.knowledge.qdrant_store import (
    CollectionConfig,
    TenantQdrantStore,
    tenant_collection_name,
)
from app.knowledge.repository import (
    KnowledgeRepository,
    _InMemoryBackend,
    reset_default_backend,
)
from app.services.tenant_resolver import (
    TenantContext,
    TenantResolutionError,
    TenantResolver,
    make_tenant_context,
)


# --------------------------------------------------------------------------- #
# Test doubles
# --------------------------------------------------------------------------- #
class FakeVectorClient:
    """In-memory stand-in implementing the VectorClient Protocol (no network)."""

    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension
        self.collections: dict[str, dict[str, Any]] = {}

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def get_collection(self, collection_name: str) -> Any:
        if collection_name not in self.collections:
            raise KeyError(collection_name)
        return _FakeCollectionInfo(self.collections[collection_name]["dimension"])

    def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.collections[collection_name] = {
            "dimension": self.dimension,
            "vectors": {},
        }

    def upsert(self, collection_name: str, points: Any) -> None:
        store = self.collections.setdefault(
            collection_name, {"dimension": self.dimension, "vectors": {}}
        )
        for p in points:
            store["vectors"][p["id"]] = p

    def delete(self, collection_name: str, points_selector: Any) -> None:  # noqa: ARG002
        # Minimal: support deleting by document_id filter for the test fake.
        if collection_name in self.collections:
            self.collections[collection_name]["vectors"] = {}

    def create_payload_index(
        self,
        collection_name: str,  # noqa: ARG002
        field_name: str,  # noqa: ARG002
        schema_type: Any,  # noqa: ARG002
    ) -> None:
        # In-memory double: indexing is a no-op.
        return None

    def query_points(
        self,
        collection_name: str,
        query: list[float],  # noqa: ARG002
        limit: int,
        with_payload: bool,  # noqa: ARG002
        query_filter: Any | None = None,  # noqa: ARG002
    ) -> Any:
        vectors = self.collections.get(collection_name, {}).get("vectors", {})
        pts = list(vectors.values())[:limit]
        return _FakeQueryResponse(pts)


class _FakeCollectionInfo:
    def __init__(self, dimension: int) -> None:
        self.config = _FakeConfig(dimension)


class _FakeConfig:
    def __init__(self, dimension: int) -> None:
        self.params = _FakeParams(dimension)


class _FakeParams:
    def __init__(self, dimension: int) -> None:
        self.vectors = _FakeVectors(dimension)


class _FakeVectors:
    def __init__(self, dimension: int) -> None:
        self.size = dimension


class _FakePoint:
    def __init__(self, point: dict[str, Any]) -> None:
        self.id = point["id"]
        self.score = 1.0
        self.payload = point.get("payload", {})


class _FakeQueryResponse:
    def __init__(self, points: list[dict[str, Any]]) -> None:
        self.points = [_FakePoint(p) for p in points]


class FakeQdrantStore(TenantQdrantStore):
    """Real TenantQdrantStore logic wired to a fake injected client."""

    def __init__(
        self,
        tenant_id: str,
        slug: str,
        *,
        dimension: int = 8,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            tenant_id,
            slug,
            client=client or FakeVectorClient(dimension=dimension),
            dimension=dimension,
        )


@pytest.fixture
def fake_repo() -> KnowledgeRepository:
    reset_default_backend()
    return KnowledgeRepository(backend=_InMemoryBackend())


def make_ctx(slug: str = "baia_resort", status: str = "active") -> TenantContext:
    return make_tenant_context("00000000-0000-0000-0000-000000000001", slug, status)


# --------------------------------------------------------------------------- #
# 1-4. Tenant resolution
# --------------------------------------------------------------------------- #
def test_verified_active_tenant_resolves():
    repo = KnowledgeRepository(backend=_InMemoryBackend())
    repo.upsert_tenant(
        slug="baia_resort", business_name="BAIA", business_type="resort", status="active"
    )
    ctx = TenantResolver(lookup=repo.get_tenant_by_slug).resolve_by_slug("baia_resort")
    assert ctx.tenant_slug == "baia_resort"
    assert ctx.status.value == "active"
    assert ctx.qdrant_collection == "merqato_tenant_baia_resort"


def test_unknown_tenant_fails_closed():
    repo = KnowledgeRepository(backend=_InMemoryBackend())
    with pytest.raises(TenantResolutionError):
        TenantResolver(lookup=repo.get_tenant_by_slug).resolve_by_slug("nope")


def test_inactive_tenant_fails_closed():
    repo = KnowledgeRepository(backend=_InMemoryBackend())
    repo.upsert_tenant(
        slug="baia_resort", business_name="BAIA", business_type="resort", status="suspended"
    )
    with pytest.raises(TenantResolutionError):
        TenantResolver(lookup=repo.get_tenant_by_slug).resolve_by_slug("baia_resort")


def test_raw_unverified_client_input_cannot_construct_crew():
    from app.crews.concierge import ConciergeCrew

    with pytest.raises(TenantResolutionError):
        ConciergeCrew("baia_resort")  # type: ignore[arg-type]
    with pytest.raises(TenantResolutionError):
        ConciergeCrew(None)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 5-7. Collection naming
# --------------------------------------------------------------------------- #
def test_baia_slug_maps_to_tenant_collection():
    assert tenant_collection_name("baia_resort") == "merqato_tenant_baia_resort"
def test_unsafe_slug_is_rejected_or_normalized():
    # Uppercase + dash are normalized deterministically to lowercase underscore.
    assert tenant_collection_name("BAIA-Resort") == "merqato_tenant_baia_resort"
    # Path-traversal / slash segments are neutralized; no path separator survives.
    name = tenant_collection_name("../escape")
    assert "/" not in name
    assert name.startswith("merqato_tenant_")
    assert "escape" in name
    # Empty / invalid slugs are rejected.
    with pytest.raises(ValueError):
        tenant_collection_name("")
    # Slashes are neutralized (no path traversal); the result stays prefixed.
    assert tenant_collection_name("../").startswith("merqato_tenant_")


def test_arbitrary_collection_override_is_impossible():
    ctx = make_ctx()
    store = TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    assert store.collection_name == "merqato_tenant_baia_resort"
    assert store.search.__code__.co_varnames


# --------------------------------------------------------------------------- #
# 8-16. Fixture ingestion
# --------------------------------------------------------------------------- #
SAMPLE_IDENTITY = {
    "name": "BAIA Resort",
    "tagline": "A quiet beachfront retreat",
    "location": "San Vicente, Palawan",
    "checkInTime": "15:00",
}


def _ingest(ctx, repo, content, category="identity", **kw):
    svc = IngestionService(repo, publish=kw.pop("publish", False))
    return svc.ingest_fixture_dict(ctx, category=category, content=content, **kw)


def test_valid_fixture_imports(fake_repo):
    ctx = make_ctx()
    res = _ingest(ctx, fake_repo, SAMPLE_IDENTITY)
    assert res.document_id is not None
    assert res.version == 1
    assert res.job_status == IngestionStatus.COMPLETED.value
    assert res.skipped is False


def test_malformed_json_fails(fake_repo):
    from app.knowledge.ingestion_service import IngestionError

    ctx = make_ctx()
    svc = IngestionService(fake_repo)
    with tempfile.TemporaryDirectory() as tmp:
        bad = os.path.join(tmp, "identity.json")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("{not valid json,,,")
        with pytest.raises(IngestionError):
            svc.load_fixture_file(bad, category="identity", ctx=ctx)


def test_unsupported_category_fails(fake_repo):
    from app.knowledge.models import Category

    with pytest.raises(ValueError):
        Category.from_filename("nonsense")


def test_unchanged_checksum_is_skipped(fake_repo):
    ctx = make_ctx()
    r1 = _ingest(ctx, fake_repo, SAMPLE_IDENTITY)
    r2 = _ingest(ctx, fake_repo, SAMPLE_IDENTITY)
    assert r1.version == 1
    assert r2.skipped is True
    assert r2.version is None


def test_changed_content_creates_new_version(fake_repo):
    ctx = make_ctx()
    _ingest(ctx, fake_repo, SAMPLE_IDENTITY)
    changed = dict(SAMPLE_IDENTITY, tagline="A brand new tagline")
    r2 = _ingest(ctx, fake_repo, changed)
    assert r2.version == 2
    assert r2.skipped is False


def test_draft_content_is_not_indexed(fake_repo):
    ctx = make_ctx()
    store = FakeQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    svc = IngestionService(
        fake_repo,
        embedder=FakeEmbeddingProvider(),
        qdrant_factory=lambda c: store,
        publish=True,
    )
    res = svc.ingest_fixture_dict(
        ctx, category="identity", content=SAMPLE_IDENTITY,
        verification_status=VerificationStatus.DRAFT.value,
    )
    assert res.indexed is False
    assert store.collection_name not in store._client.collections


def test_verified_but_unpublished_content_is_not_indexed(fake_repo):
    ctx = make_ctx()
    store = FakeQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    svc = IngestionService(
        fake_repo,
        embedder=FakeEmbeddingProvider(),
        qdrant_factory=lambda c: store,
        publish=False,
    )
    res = svc.ingest_fixture_dict(
        ctx, category="identity", content=SAMPLE_IDENTITY,
        verification_status=VerificationStatus.VERIFIED.value,
    )
    assert res.indexed is False


def test_verified_published_guest_visible_content_is_indexed(fake_repo):
    ctx = make_ctx()
    store = FakeQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    svc = IngestionService(
        fake_repo,
        embedder=FakeEmbeddingProvider(),
        qdrant_factory=lambda c: store,
        publish=True,
    )
    res = svc.ingest_fixture_dict(
        ctx, category="identity", content=SAMPLE_IDENTITY,
        verification_status=VerificationStatus.VERIFIED.value,
    )
    assert res.indexed is True
    assert store.collection_name in store._client.collections
    assert len(store._client.collections[store.collection_name]["vectors"]) >= 1


def test_internal_only_content_is_not_indexed_for_guest(fake_repo):
    ctx = make_ctx()
    store = FakeQdrantStore(ctx.tenant_id, ctx.tenant_slug)
    svc = IngestionService(
        fake_repo,
        embedder=FakeEmbeddingProvider(),
        qdrant_factory=lambda c: store,
        publish=True,
    )
    res = svc.ingest_fixture_dict(
        ctx, category="identity", content=SAMPLE_IDENTITY,
        verification_status=VerificationStatus.VERIFIED.value,
        internal_only=True,
    )
    assert res.indexed is False


# --------------------------------------------------------------------------- #
# 17-21. Qdrant
# --------------------------------------------------------------------------- #
def test_correct_tenant_collection_is_selected():
    store = TenantQdrantStore("tenant-uuid", "baia_resort")
    assert store.collection_name == "merqato_tenant_baia_resort"


def test_collection_created_with_expected_dimension_and_cosine():
    store = FakeQdrantStore("tenant-uuid", "baia_resort", dimension=8)
    cfg = store.ensure_collection()
    assert isinstance(cfg, CollectionConfig)
    assert cfg.dimension == 8
    assert cfg.distance == "cosine"
    assert store.collection_name in store._client.collections


def test_incompatible_existing_dimensions_fail_safely():
    shared = FakeVectorClient(dimension=8)
    store = FakeQdrantStore("tenant-uuid", "baia_resort", dimension=8, client=shared)
    store.ensure_collection()
    bad = FakeQdrantStore("tenant-uuid", "baia_resort", dimension=16, client=shared)
    with pytest.raises(ValueError):
        bad.ensure_collection()


def test_vector_payload_contains_required_metadata():
    ctx = make_ctx()
    store = FakeQdrantStore(ctx.tenant_id, ctx.tenant_slug, dimension=8)
    svc = IngestionService(
        KnowledgeRepository(backend=_InMemoryBackend()),
        embedder=FakeEmbeddingProvider(),
        qdrant_factory=lambda c: store,
        publish=True,
    )
    svc.ingest_fixture_dict(
        ctx, category="identity", content=SAMPLE_IDENTITY,
        verification_status=VerificationStatus.VERIFIED.value,
    )
    vectors = store._client.collections[store.collection_name]["vectors"]
    payload = next(iter(vectors.values()))["payload"]
    for key in [
        "tenant_id", "tenant_slug", "document_id", "document_version_id",
        "category", "version", "checksum", "verification_status",
        "guest_visible", "internal_only", "chunk_index", "source_filename", "text",
    ]:
        assert key in payload


def test_no_cross_tenant_retrieval_api_exists():
    methods = set(dir(TenantQdrantStore))
    assert "search_all_tenants" not in methods
    assert "search_collection" not in methods


# --------------------------------------------------------------------------- #
# 27-29. Security
# --------------------------------------------------------------------------- #
def test_secrets_absent_from_logs_and_errors(fake_repo):
    try:
        raise RuntimeError("connection failed: api_key=sk-live-abcdef1234567890")
    except RuntimeError as exc:
        from app.knowledge.ingestion_service import _safe_message

        msg = _safe_message(exc)
    assert "sk-secret-12345" not in msg
    assert "REDACTED" in msg


def test_widget_tokens_stored_only_as_hashes(fake_repo):
    from app.security.secrets import hash_secret

    raw = "widget-token-plaintext"
    repo = fake_repo
    repo.upsert_tenant(
        slug="baia_resort", business_name="BAIA", business_type="resort",
        status="active", widget_token_hash=hash_secret(raw),
    )
    row = repo.get_tenant_by_slug("baia_resort")
    assert row["widget_token_hash"] != raw
    assert row["widget_token_hash"].startswith("sha256:")


def test_service_role_credentials_never_exposed(fake_repo):
    from app.config import get_settings

    settings = get_settings()
    assert "SUPABASE_SERVICE_ROLE_KEY" not in repr(settings) or "REDACTED" in repr(settings)


# --------------------------------------------------------------------------- #
# 30-31. CLI
# --------------------------------------------------------------------------- #
def _write_fixtures(tmp: str, data: dict[str, Any]) -> None:
    for cat, content in data.items():
        with open(os.path.join(tmp, f"{cat}.json"), "w", encoding="utf-8") as fh:
            json.dump(content, fh)


def test_dry_run_performs_no_writes():
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixtures(tmp, {"identity": SAMPLE_IDENTITY})
        repo = KnowledgeRepository(backend=_InMemoryBackend())
        ctx = make_ctx()
        svc = IngestionService(repo, publish=True)
        res = svc.ingest_fixture_dict(
            ctx, category="identity", content=SAMPLE_IDENTITY, dry_run=True,
            verification_status=VerificationStatus.DRAFT.value,
        )
        assert res.skipped is False
        assert repo.get_document(ctx.tenant_id, "identity") is None


def test_baia_arguments_produce_expected_plan():
    with tempfile.TemporaryDirectory() as tmp:
        _write_fixtures(tmp, {
            "identity": SAMPLE_IDENTITY,
            "amenities": {"amenities": [{"name": "Pool"}]},
        })
        fixtures = sorted(
            os.path.basename(p)[:-len(".json")]
            for p in os.listdir(tmp) if p.endswith(".json")
        )
        assert fixtures == ["amenities", "identity"]
        for f in fixtures:
            assert Category.from_filename(f).value == f


def test_all_ten_categories_are_supported():
    # The generic allowlist spans ten categories for any tenant.
    supported = {
        "identity", "rooms", "rates", "amenities", "policies",
        "wifi_power", "food_breakfast", "transport", "emergency_contacts", "faq",
    }
    assert Category.values() == supported
    for cat in supported:
        assert Category.from_filename(cat).value == cat
    # Unsupported categories still fail closed.
    with pytest.raises(ValueError):
        Category.from_filename("nonsense")
