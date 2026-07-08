# CODEBASE.md

Orientation map for `merqato-ai-resort-platform` (backend).

## Repository purpose

Multi-tenant knowledge ingestion + AI concierge backend for MerQato resort
customers. Supabase (PostgreSQL + pgvector) is the **source of truth**; Qdrant
holds per-tenant vector indexes for guest retrieval; the FastAPI + CrewAI agent
service answers guest questions using verified tenant knowledge only.

> This repository is the **backend**. The public BAIA website lives in a
> separate repository (`merqatodigital/BAIA-San-Vicente-Palawan-Island`) and is
> never modified from here.

## Top-level layout

| Path | Purpose |
|------|---------|
| `services/agent-api/` | FastAPI + CrewAI agent service (the only production agent engine) |
| `supabase/schema.sql` | Idempotent multi-tenant knowledge schema (tables, indexes, RLS) |
| `fixtures/baia_resort/` | Verified BAIA factual knowledge (10 categories, draft) |
| `fixtures/template/` | Reusable generic templates (placeholders only) |
| `fixtures/shared/san_vicente/` | Shared regional knowledge — NOT attached to any tenant |
| `docs/` | Deployment + knowledge-architecture documentation |
| `src/` `public/` | Frontend (Next.js) — BFF proxy only, no agent logic |

## `services/agent-api` layout

```
app/
  main.py                 # FastAPI app + /health + /v1/concierge/message
  config.py               # Supabase / Qdrant / embedding configuration
  models/schemas.py       # Pydantic request/response models
  security/secrets.py     # redact() / hash_secret() / safe_log() — no secret leakage
  knowledge/
    models.py             # Category (10), VerificationStatus, etc.
    formatter.py          # factual JSON -> deterministic semantic text
    chunker.py            # recursive chunking (per-tenant, no cross-tenant mix)
    embeddings.py         # embedding provider interface + FakeEmbeddingProvider
    repository.py         # KnowledgeRepository (in-memory default + Supabase)
    ingestion_service.py  # lifecycle: parse -> store -> (publish) -> index
    qdrant_store.py       # TenantQdrantStore (server-generated collection name)
    sample_repository.py  # legacy sample (clearly labeled NOT production data)
  services/
    tenant_resolver.py    # TenantResolver — fail-closed tenant resolution
    concierge_service.py  # builds TenantContext, runs the crew
    openrouter_validate.py# customer key validation (key never returned)
  crews/concierge/
    crew.py               # CrewAI Crew/Agent/Task + TenantKnowledgeTool
    config/               # agents.yaml / tasks.yaml
  scripts/seed_tenant.py  # CLI: seed a tenant from fixtures (dry-run safe)
tests/                    # pytest suite (fakes/mocks; no live network)
```

## Invariants (enforced in code)

- Tenant resolution **fails closed**: only `active` tenants resolve for runtime
  guest retrieval. draft / suspended / archived / unknown → rejected.
- Only `verified + published + guest_visible + not internal_only` versions are
  eligible for Qdrant indexing.
- Qdrant collection names are **server-generated** (`merqato_tenant_<slug>`);
  clients never supply a collection name.
- No raw widget token is stored — only `widget_token_hash`.
- No BAIA facts are hardcoded in application code; all knowledge comes from
  Supabase (seeded from fixtures).
- Secrets are redacted before logging (`app/security/secrets.py`).

## Local development (agent-api)

```bash
cd services/agent-api
python -m venv .venv && .venv/Scripts/activate
pip install -e .
PYTHONPATH= .venv/Scripts/python -m pytest          # tests
PYTHONPATH= .venv/Scripts/python -m ruff check app tests
PYTHONPATH= .venv/Scripts/python -m mypy app
uvicorn app.main:app --port 8000 --reload
```

> The Hermes desktop terminal injects a `PYTHONPATH` that contaminates the
> project venv — always prefix Python commands with `PYTHONPATH=` here.

## Seeding a tenant (dry-run, no writes)

```bash
PYTHONPATH= .venv/Scripts/python -m app.scripts.seed_tenant \
  --tenant-slug baia_resort \
  --business-name "BAIA - Beachfront Boutique Lodge in San Vicente, Palawan" \
  --business-type resort \
  --fixtures-path fixtures/baia_resort \
  --dry-run
```
