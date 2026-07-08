# DEPLOYMENT.md

Deployment guidance for `merqato-ai-resort-platform` (backend).

> Scope of this document: backend service + Supabase schema + Qdrant. Railway
> deployment and public website integration are covered elsewhere and are NOT
> performed in the knowledge-seeding phase.

## Prerequisites

- GitHub repo: `merqatodigital/merqato-ai-resort-platform` (private)
- Supabase project (PostgreSQL + pgvector enabled)
- Qdrant instance (per-tenant collections)
- OpenRouter key supplied per resort customer (never MerQato's)

## 1. Apply the database schema

`supabase/schema.sql` is **idempotent** (`create table if not exists`,
`create index if not exists`, `create policy if not exists`) and expands the
category CHECK constraint safely on existing databases via an `ALTER` block.

Apply via the Supabase SQL editor, `supabase db push`, or `psql` using the
**service-role / DB URL** (server-secret only — never committed):

```bash
psql "$SUPABASE_DB_URL" -f supabase/schema.sql
```

Objects created:

- `tenants` — tenant registry (slug unique, status constraint)
- `tenant_knowledge_documents` — stable logical document per (tenant, category)
- `tenant_knowledge_versions` — immutable factual history (content jsonb)
- `knowledge_ingestion_jobs` — job tracking
- `knowledge_audit_logs` — audit trail
- Indexes on `tenants(slug)` and tenant_id columns
- RLS **enabled** on all five tables; `service_role` full-access policies
- Category CHECK constraint: exactly the ten supported categories

RLS must remain **enabled** in every environment.

## 2. Configure environment

Copy `.env.example` → `.env` (server) and fill in the documented variable
names only. Required for live operation:

```
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_DB_URL
OPENROUTER_API_KEY
QDRANT_URL
QDRANT_API_KEY
TENANT_SLUG
TENANT_DOMAIN
AGENT_API_URL
```

Never commit real values. Use your secret manager / CI secrets.

## 3. Run the agent service

```bash
cd services/agent-api
pip install -e .
uvicorn app.main:app --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
# { "status": "ok", "crewai_version": "...", "openrouter_configured": true }
```

## 4. Seed a tenant (draft, no publish, no Qdrant)

```bash
PYTHONPATH= .venv/Scripts/python -m app.scripts.seed_tenant \
  --tenant-slug baia_resort \
  --business-name "BAIA - Beachfront Boutique Lodge in San Vicente, Palawan" \
  --business-type resort \
  --fixtures-path fixtures/baia_resort \
  --verification-status draft \
  --dry-run            # validate first; performs zero writes
```

Remove `--dry-run` to write to Supabase (still `publish=false` unless
`--publish` + `--verification-status verified` are both set). Qdrant indexing
only happens on verified + published + guest_visible content.

## Verification checklist (after seeding)

- [ ] Exactly one tenant row (`baia_resort`).
- [ ] Exactly 10 current knowledge documents, one per category.
- [ ] Raw root JSON stored in `content` (no wrapper).
- [ ] Versions created; `verification_status = draft`.
- [ ] No published documents; `published_at IS NULL`.
- [ ] Ingestion job recorded; audit logs created.
- [ ] No Qdrant writes (indexing not triggered for draft).
- [ ] RLS still enabled on all tables.

## Rollback

The schema uses immutable version rows; editing a document creates a new
version rather than overwriting. To "unpublish", set the relevant version's
`verification_status` / `guest_visible` / `published_at` via a new version — do
not `UPDATE` historical rows in place.
