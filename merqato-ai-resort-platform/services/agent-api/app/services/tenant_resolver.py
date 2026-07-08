from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass

from app.config import get_settings
from app.knowledge.qdrant_store import tenant_collection_name


class TenantStatus(enum.StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class TenantContext:
    """Verified, server-side tenant identity for downstream retrieval.

    Constructed ONLY by the tenant resolver after verifying the tenant exists
    and is in an allowed status. Carries the internal UUID, the routing slug,
    the status, and the deterministic Qdrant collection name. Never built
    directly from a raw client-supplied tenant id.
    """

    tenant_id: str
    tenant_slug: str
    status: TenantStatus
    qdrant_collection: str


class TenantResolutionError(Exception):
    """Raised when a tenant cannot be resolved or is not permitted."""


# Statuses that may serve guest retrieval. Suspended/archived/draft may not.
_ALLOWED_STATUSES = frozenset({TenantStatus.ACTIVE})


def _build_collection_name(slug: str) -> str:
    """Deterministic, server-generated Qdrant collection name.

    Delegated to the central naming function in app.knowledge.qdrant_store so
    the rule lives in exactly one place.
    """
    return tenant_collection_name(slug)


class TenantResolver:
    """Resolves tenants from trusted server-side routing context.

    Backed by an injectable lookup callable so tests can supply controlled
    tenant records without a live Supabase connection. The production lookup
    (Supabase) is wired in later; the resolver itself never trusts a raw
    client-supplied tenant id on its own.
    """

    def __init__(
        self,
        lookup: Callable[[str], dict | None] | None = None,
    ) -> None:
        self._settings = get_settings()
        # lookup(slug) -> tenant row dict or None. Defaults to a no-op so the
        # resolver fails closed when no backend is configured.
        self._lookup = lookup or (lambda _slug: None)

    def resolve_by_slug(self, slug: str) -> TenantContext:
        """Resolve a tenant by its trusted server-side slug routing context."""
        if not slug or not isinstance(slug, str):
            raise TenantResolutionError("tenant slug is required")
        row = self._lookup(slug)
        if row is None:
            raise TenantResolutionError(f"unknown tenant slug: {slug!r}")
        status_raw = row.get("status", "draft")
        try:
            status = TenantStatus(status_raw)
        except ValueError as err:
            raise TenantResolutionError(f"invalid tenant status: {status_raw!r}") from err
        if status not in _ALLOWED_STATUSES:
            raise TenantResolutionError(
                f"tenant {slug!r} is not active (status={status.value})"
            )
        return TenantContext(
            tenant_id=str(row["id"]),
            tenant_slug=slug,
            status=status,
            qdrant_collection=_build_collection_name(slug),
        )

    def resolve_by_id(self, tenant_id: str) -> TenantContext:
        """Resolve by internal UUID. Still requires a verified backend lookup,
        never a raw client-supplied id used to skip validation."""
        if not tenant_id or not isinstance(tenant_id, str):
            raise TenantResolutionError("tenant id is required")
        row = self._lookup_by_id(tenant_id)
        if row is None:
            raise TenantResolutionError(f"unknown tenant id: {tenant_id!r}")
        return self.resolve_by_slug(row["slug"])

    def _lookup_by_id(self, tenant_id: str) -> dict | None:
        # The tenant store can resolve by id too; default lookup is slug-based,
        # so we wrap by scanning via a slug-agnostic callable if provided.
        if getattr(self._lookup, "by_id", None) is not None:  # pragma: no cover
            return self._lookup.by_id(tenant_id)  # type: ignore[attr-defined]
        return None


def require_tenant_context(ctx: TenantContext | None) -> TenantContext:
    """Fail-closed guard: tenant knowledge retrieval requires verified context."""
    if ctx is None or not isinstance(ctx, TenantContext):
        raise TenantResolutionError("verified tenant context is required")
    return ctx


def make_tenant_context(
    tenant_id: str, tenant_slug: str, status: str = "active"
) -> TenantContext:
    """Construct a verified tenant context for tests / controlled internal use.

    Production code MUST go through TenantResolver.resolve_by_slug / _by_id so the
    tenant is actually verified. This helper is for callers that already hold a
    verified tenant record (unit tests, the CLI after explicit resolution).
    """
    return TenantContext(
        tenant_id=str(tenant_id),
        tenant_slug=tenant_slug,
        status=TenantStatus(status),
        qdrant_collection=tenant_collection_name(tenant_slug),
    )
