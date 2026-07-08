"""Admin knowledge-management API (server-to-server only).

Every route:
  * requires the shared ``X-Admin-Token`` secret (fail closed when unset) —
    the Next.js BFF holds the token server-side; browsers never call this API;
  * is tenant-scoped via the URL slug — the tenant must exist (draft tenants
    ARE manageable here; only guest retrieval requires an active tenant);
  * goes through the repository/PublishingService layer, never raw tables.
"""

from __future__ import annotations

import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.knowledge.embeddings import EmbeddingNotConfigured, get_embedding_provider
from app.knowledge.publishing_service import (
    DuplicateContentError,
    PublishingError,
    PublishingService,
    PublishStateError,
)
from app.knowledge.qdrant_store import TenantQdrantStore
from app.knowledge.repository import KnowledgeRepository
from app.services.tenant_resolver import TenantContext, make_tenant_context

router = APIRouter(prefix="/v1/admin/tenants/{slug}/knowledge")


# --- auth -------------------------------------------------------------------
def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    expected = get_settings().admin_api_token
    if not expected:
        # Fail closed: without a configured secret the admin API is disabled.
        raise HTTPException(status_code=503, detail="admin API is not configured")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=401, detail="invalid admin credentials")


# --- helpers ------------------------------------------------------------------
def _admin_ctx(slug: str) -> TenantContext:
    """Resolve a tenant for ADMIN management (any lifecycle status)."""
    repo = KnowledgeRepository()
    row = repo.get_tenant_by_slug(slug)
    if row is None:
        raise HTTPException(status_code=404, detail="unknown tenant")
    return make_tenant_context(row["id"], row["slug"], row.get("status", "draft"))


def _read_service() -> PublishingService:
    return PublishingService(KnowledgeRepository())


def _write_service() -> PublishingService:
    """Service able to (un)publish. Embeddings/Qdrant fail closed via 503."""
    try:
        embedder = get_embedding_provider()
    except EmbeddingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PublishingService(
        KnowledgeRepository(),
        embedder=embedder,
        qdrant_factory=lambda ctx: TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug),
    )


def _unpublish_service() -> PublishingService:
    """Unpublishing removes vectors — needs Qdrant but not embeddings, so it
    stays available even when the embedding provider is down."""
    return PublishingService(
        KnowledgeRepository(),
        qdrant_factory=lambda ctx: TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug),
    )


def _translate(exc: PublishingError) -> HTTPException:
    if isinstance(exc, DuplicateContentError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, PublishStateError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=502, detail=str(exc))


# --- schemas ------------------------------------------------------------------
class DraftRequest(BaseModel):
    content: dict[str, Any]
    guest_visible: bool = True
    internal_only: bool = False
    actor_id: str | None = Field(default=None, max_length=200)


class UnpublishRequest(BaseModel):
    archive: bool = False
    actor_id: str | None = Field(default=None, max_length=200)


class ActorRequest(BaseModel):
    actor_id: str | None = Field(default=None, max_length=200)


# --- reads --------------------------------------------------------------------
@router.get("/categories", dependencies=[Depends(require_admin_token)])
def list_categories(slug: str) -> list[dict[str, Any]]:
    return _read_service().list_categories(_admin_ctx(slug))


@router.get("/{category}/current", dependencies=[Depends(require_admin_token)])
def get_current_version(slug: str, category: str) -> dict[str, Any]:
    try:
        result = _read_service().get_current(_admin_ctx(slug), category)
    except ValueError as exc:  # unsupported category
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="no document for this category yet")
    return result


@router.get("/{category}/versions", dependencies=[Depends(require_admin_token)])
def list_version_history(slug: str, category: str) -> list[dict[str, Any]]:
    try:
        return _read_service().list_versions(_admin_ctx(slug), category)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{category}/audits", dependencies=[Depends(require_admin_token)])
def list_audit_history(slug: str, category: str) -> list[dict[str, Any]]:
    try:
        return _read_service().list_audits(_admin_ctx(slug), category)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs", dependencies=[Depends(require_admin_token)])
def list_ingestion_jobs(
    slug: str, version_id: str | None = None
) -> list[dict[str, Any]]:
    return _read_service().list_jobs(
        _admin_ctx(slug), document_version_id=version_id
    )


# --- writes -------------------------------------------------------------------
@router.post("/{category}/draft", dependencies=[Depends(require_admin_token)])
def create_draft_version(slug: str, category: str, req: DraftRequest) -> dict[str, Any]:
    try:
        return _read_service().create_draft(
            _admin_ctx(slug),
            category=category,
            content=req.content,
            guest_visible=req.guest_visible,
            internal_only=req.internal_only,
            actor_id=req.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PublishingError as exc:
        raise _translate(exc) from exc


@router.post(
    "/versions/{version_id}/verify", dependencies=[Depends(require_admin_token)]
)
def verify_version(slug: str, version_id: str, req: ActorRequest) -> dict[str, Any]:
    try:
        return _read_service().verify(
            _admin_ctx(slug), version_id, actor_id=req.actor_id
        )
    except PublishingError as exc:
        raise _translate(exc) from exc


@router.post(
    "/versions/{version_id}/publish", dependencies=[Depends(require_admin_token)]
)
def publish_version(slug: str, version_id: str, req: ActorRequest) -> dict[str, Any]:
    try:
        return _write_service().publish(
            _admin_ctx(slug), version_id, actor_id=req.actor_id
        )
    except PublishingError as exc:
        raise _translate(exc) from exc


@router.post(
    "/versions/{version_id}/unpublish", dependencies=[Depends(require_admin_token)]
)
def unpublish_version(
    slug: str, version_id: str, req: UnpublishRequest
) -> dict[str, Any]:
    try:
        return _unpublish_service().unpublish(
            _admin_ctx(slug), version_id, archive=req.archive, actor_id=req.actor_id
        )
    except PublishingError as exc:
        raise _translate(exc) from exc
