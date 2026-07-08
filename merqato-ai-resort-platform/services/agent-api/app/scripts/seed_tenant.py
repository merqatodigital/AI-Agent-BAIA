from __future__ import annotations

import argparse
import json
import os
import sys

from app.knowledge.embeddings import FakeEmbeddingProvider
from app.knowledge.ingestion_service import IngestionService
from app.knowledge.models import Category, VerificationStatus
from app.knowledge.qdrant_store import TenantQdrantStore
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.supabase_backend import SupabaseBackend
from app.services.tenant_resolver import TenantContext, TenantResolver

SUPPORTED = Category.values()


def _build_repository(args: argparse.Namespace) -> KnowledgeRepository:
    """Use the live Supabase backend when service-role creds are present and
    this is not a dry run; otherwise the in-memory backend (tests/dry-run)."""
    if args.dry_run:
        return KnowledgeRepository()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        return KnowledgeRepository(backend=SupabaseBackend(url, key))
    print(
        "WARNING: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not set; using in-memory backend.",
        file=sys.stderr,
    )
    return KnowledgeRepository()


def _normalize_fixture_path(path: str) -> str:
    # Allow "fixtures/baia_resort" or ".../fixtures/baia_resort"
    if os.path.isdir(path):
        return path
    if os.path.isfile(path):
        return os.path.dirname(path)
    raise SystemExit(f"fixture path not found: {path}")


def _discover_fixtures(fixtures_dir: str) -> list[tuple[str, str]]:
    """Return list of (category, absolute_json_path). Reject non-.json files."""
    found: list[tuple[str, str]] = []
    for name in sorted(os.listdir(fixtures_dir)):
        full = os.path.join(fixtures_dir, name)
        if not os.path.isfile(full):
            continue
        if not name.endswith(".json"):
            raise SystemExit(f"only .json fixtures allowed; found: {name}")
        stem = name[: -len(".json")]
        if stem not in SUPPORTED:
            raise SystemExit(f"unsupported category from filename: {stem!r}")
        found.append((stem, full))
    if not found:
        raise SystemExit(f"no valid .json fixtures in {fixtures_dir}")
    return found


def _qdrant_factory(ctx: TenantContext) -> TenantQdrantStore:
    return TenantQdrantStore(ctx.tenant_id, ctx.tenant_slug)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed a MerQato tenant from factual JSON fixtures."
    )
    parser.add_argument("--tenant-slug", required=True)
    parser.add_argument("--business-name", required=True)
    parser.add_argument("--business-type", required=True)
    parser.add_argument("--fixtures-path", required=True)
    parser.add_argument(
        "--verification-status",
        default=VerificationStatus.DRAFT.value,
        choices=sorted(VerificationStatus.values()),
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Mark verified content as published and trigger Qdrant indexing.",
    )
    parser.add_argument(
        "--status",
        default="draft",
        help="Tenant lifecycle status (draft|active|suspended|archived).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize without writing to Supabase or Qdrant.",
    )
    args = parser.parse_args(argv)

    fixtures_dir = _normalize_fixture_path(args.fixtures_path)
    fixtures = _discover_fixtures(fixtures_dir)

    repo = _build_repository(args)
    resolver = TenantResolver(lookup=repo.get_tenant_by_slug)

    # Create or locate the tenant (no overwrite of existing business data).
    if repo.get_tenant_by_slug(args.tenant_slug) is None:
        repo.upsert_tenant(
            slug=args.tenant_slug,
            business_name=args.business_name,
            business_type=args.business_type,
            status=args.status,
        )

    # Resolve context for downstream ingestion. A brand-new or not-yet-active
    # tenant (e.g. draft) is allowed to be seeded by an operator, but runtime
    # guest retrieval still fails closed via TenantResolver. For seeding we
    # build the context directly from the tenant row when resolution is denied.
    tenant_row = repo.get_tenant_by_slug(args.tenant_slug)
    try:
        ctx = resolver.resolve_by_slug(args.tenant_slug)
    except Exception as exc:  # noqa: BLE001
        if tenant_row is None:
            print(f"ERROR: cannot resolve tenant for seeding: {exc}", file=sys.stderr)
            return 2
        # Operator seeding of a draft/new tenant: build context from the row.
        from app.services.tenant_resolver import TenantStatus

        ctx = TenantContext(
            tenant_id=tenant_row["id"],
            tenant_slug=tenant_row["slug"],
            status=TenantStatus(tenant_row.get("status", "draft")),
            qdrant_collection=TenantQdrantStore(
                tenant_row["id"], tenant_row["slug"]
            ).collection_name,
        )

    # Build ingestion service (dry-run => no embedder/store writes).
    publish = args.publish and args.verification_status == VerificationStatus.VERIFIED.value
    service = IngestionService(
        repo,
        embedder=FakeEmbeddingProvider() if (publish and not args.dry_run) else None,
        qdrant_factory=_qdrant_factory if (publish and not args.dry_run) else None,
        publish=publish,
    )

    print(f"Tenant: {ctx.tenant_slug} (id={ctx.tenant_id}, status={ctx.status.value})")
    print(f"Fixtures: {fixtures_dir}")
    print(f"Verification: {args.verification_status}  Publish: {publish}  Dry-run: {args.dry_run}")
    print("Plan:")
    results = []
    for category, path in fixtures:
        with open(path, encoding="utf-8") as fh:
            try:
                content = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"  [FAIL] {category}: malformed JSON: {exc}", file=sys.stderr)
                return 2
        res = service.ingest_fixture_dict(
            ctx,
            category=category,
            content=content,
            source_filename=os.path.basename(path),
            verification_status=args.verification_status,
            dry_run=args.dry_run,
        )
        results.append(res)
        flag = "skip(dup)" if res.skipped else ("indexed" if res.indexed else "stored")
        print(f"  - {category}: {flag} checksum={res.checksum[:12]}...")

    if args.dry_run:
        print("DRY-RUN: no writes performed.")
    else:
        print(f"Seeded {len(results)} categories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
