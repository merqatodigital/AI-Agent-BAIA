# KNOWLEDGE_ARCHITECTURE.md

How multi-tenant knowledge is stored, ingested, and retrieved.

## Principles

1. **Supabase is the source of truth.** Documents and their immutable version
   history live in PostgreSQL. Qdrant is a derived index, never the system of
   record.
2. **Tenant isolation is structural, not advisory.** Each tenant gets a
   server-generated Qdrant collection; retrieval is scoped to that collection.
3. **Fail closed.** Unknown / inactive / suspended / archived / draft tenants
   cannot be resolved for runtime guest retrieval.
4. **Verified-only indexing.** Only `verified + published + guest_visible +
   not internal_only` versions are indexed into Qdrant.
5. **No BAIA facts in code.** All factual knowledge is seeded from fixtures
   into Supabase; application code contains none.

## Data model

```
tenants (slug, business_name, business_type, status)
   │ 1
   ├──< tenant_knowledge_documents (tenant_id, category, current_version)
   │        │ 1
   │        └──< tenant_knowledge_versions
   │                 (document_id, version, content jsonb, checksum,
   │                  verification_status, guest_visible, internal_only,
   │                  published_at, approved_by, approved_at)
   ├──< knowledge_ingestion_jobs (tenant_id, document_version_id, status, ...)
   └──< knowledge_audit_logs (tenant_id, action, actor_type, metadata)
```

- `tenant_knowledge_documents` is the stable logical document. One row per
  `(tenant_id, category)`.
- `tenant_knowledge_versions` is **immutable**: every edit appends a new
  version (never `UPDATE` in place). `unique (tenant_id, checksum)` prevents
  duplicate storage of identical content.
- Constraints guarantee correctness:
  - `not (internal_only = true and guest_visible = true)`
  - `published_at is null or verification_status = 'verified'`

## Knowledge categories (exactly ten, generic)

```
identity  rooms  rates  amenities  policies
wifi_power  food_breakfast  transport  emergency_contacts  faq
```

The allowlist lives in `app/knowledge/models.py` (`Category` StrEnum) and is
mirrored by the Supabase CHECK constraint. Unsupported filenames fail closed
during ingestion.

## Ingestion contract

A fixture file `<category>.json`:

- **filename stem → `category`** (validated against the allowlist)
- **entire root JSON object → `content`** (no redundant wrapper)
- no code expects `content[category]`

Examples:

- `policies.json` → category `policies`, content = full root object
- `faq.json` → category `faq`, content = `{ "faqs": [...] }`

Behavior: parse the full root object, preserve nested objects, arrays,
booleans, numbers, nulls, and strings. Do not flatten meaning, invent values,
or rewrite verified facts.

## Ingestion lifecycle

`IngestionService.ingest_fixture_dict(...)`:

1. Parse + canonicalize (sorted keys for stable checksums).
2. Compute checksum; skip if identical version already exists.
3. Upsert `tenant_knowledge_documents` (one per category).
4. Append a `tenant_knowledge_versions` row.
5. If `publish` and `verification_status == verified` and not `internal_only`
   and `guest_visible`:
   - chunk + embed + upsert into the tenant's Qdrant collection.
6. Record an ingestion job + audit log entry.

With `dry_run=True`, steps 3–6 are skipped (zero writes).

## Retrieval (guest path)

1. `TenantResolver.resolve_by_slug(slug)` → `TenantContext` (fails closed
   unless `status == active`).
2. The concierge crew receives a `TenantKnowledgeTool` bound to the resolved
   `TenantContext`. The tool queries **only** that tenant's Qdrant collection.
3. Retrieved chunks cite the source category + document version (provenance).

## Shared vs tenant knowledge

Shared regional knowledge (e.g. `fixtures/shared/san_vicente/`) is preserved
**separately** and is **not** auto-attached to any tenant. There is no implicit
shared fallback in retrieval. Future shared scope is opt-in per tenant.

## Formatting & chunking

- `formatter.format_knowledge(category, content)` → deterministic semantic
  text (field names + values, nested meaning preserved, no behavioral
  instructions injected).
- `chunker.chunk_document(...)` → recursive chunks; each chunk carries its
  category + source filename. Chunks never mix tenants or merge separate files.

## Seeding

`app/scripts/seed_tenant.py` ingests a tenant's fixtures. It creates the tenant
row if absent (default `draft`) and (for operator seeding) builds the context
directly when resolution is denied for a not-yet-active tenant. Runtime guest
retrieval still goes exclusively through `TenantResolver`.
