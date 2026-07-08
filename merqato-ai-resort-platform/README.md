# MerQato AI Resort Website

A commercial, AI-powered website platform for small resorts, boutique hotels,
villas and homestays. Each customer gets a complete luxury website with an
integrated AI concierge, admin dashboard, owner Mission Control, staff
operations, and human-approval workflows.

## Stack
- Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 — public site, guest concierge UI, admin & Mission Control
- **FastAPI (Python) + the actual CrewAI framework** — dedicated agent service (`services/agent-api`). This is the *only* production agent engine.
- OpenRouter for LLMs — **customer supplies their own key** (read by the agent service)
- Supabase (PostgreSQL + pgvector + Auth + Storage) — optional

> **Architecture note:** The Next.js app contains **no agent logic**. Its
> `/api/agent` route is a thin BFF proxy that forwards guest messages to the
> FastAPI service's real CrewAI concierge (`POST /v1/concierge/message`). The
> homemade "CrewAI-style" TypeScript runner that previously lived in
> `src/lib/agents` has been removed.

## Quick start (zero config)
```bash
pnpm install
pnpm dev
```
The app boots with a seeded in-memory demo resort (Kapwa Bay Resort) so every
page and the AI concierge run without any external service.

## Connect your own services
Copy `.env.example` to `.env.local` and fill in:
- `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` (or
  `SUPABASE_SERVICE_ROLE_KEY`) — switches the data layer from dev to Supabase.
  Run `supabase/schema.sql` in your Supabase project first.
- `OPENROUTER_API_KEY` — the **customer's** key. The concierge and agents then
  answer using the resort knowledge base on the customer's own OpenRouter
  account (MerQato never bills for tokens).
- `OPENROUTER_MODEL` — default model (e.g. `openai/gpt-4o-mini`).

## Safety rules (enforced in code)
The AI can NEVER autonomously: confirm/cancel bookings, refund, charge cards,
publish posts, delete records, or change prices. Every sensitive action is
routed to an owner approval queue (`/admin/approvals`).

## Scripts
- `pnpm dev` / `pnpm build` / `pnpm start`
- `pnpm exec tsc --noEmit` — typecheck
- `pnpm run lint` — eslint
- `pnpm exec vitest run` — tests

## Project layout
- `src/lib/data` — DataStore interface + dev & Supabase adapters
- `src/lib/concierge-ui.ts` — concierge page UI-only constants (suggested questions, topics)
- `src/app/api/openrouter/route.ts` — BFF proxy to FastAPI `/v1/openrouter/validate`
- `src/app` — pages (`/`, `/concierge`, `/admin/*`) + API routes
- `src/app/api/agent/route.ts` — **BFF proxy** to FastAPI `/v1/concierge/message`
- `services/agent-api` — FastAPI + CrewAI agent service (the agent engine)
- `supabase/schema.sql` — database schema
- `THIRD_PARTY_NOTICES.md` — CrewAI (MIT) and other license notices

## Agent service (services/agent-api)

FastAPI + real CrewAI. The concierge builds actual `crewai.Agent` /
`crewai.Task` / `crewai.Crew` objects and runs them against OpenRouter
(`provider="openrouter"`). OpenRouter is configured **per request** from the
resort's own key (`OPENROUTER_API_KEY`) and is never exposed to the browser,
logs, or API responses.

Endpoints:
- `GET /health` → `{status, crewai_version, environment, openrouter_configured}`
- `POST /v1/concierge/message` →
  `{reply, intent, confidence, sources, proposed_actions, requires_approval, escalation_reason}`

## Local development

### Frontend only
```bash
pnpm install
pnpm dev        # http://localhost:3000
```
The concierge `/api/agent` proxies to `AGENT_API_URL` (default
`http://localhost:8000`). If the agent service is not running, the proxy
returns a controlled "unreachable" response (no fabricated answers).

### Agent API only
```bash
cd services/agent-api
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e .
uvicorn app.main:app --port 8000 --reload
# http://localhost:8000/health
```
Set `OPENROUTER_API_KEY` (the customer's key) to enable live concierge replies.
Without it, `/v1/concierge/message` returns a controlled 503.

### Both services together (two terminals)
```bash
# Terminal 1 — agent service
cd services/agent-api && uvicorn app.main:app --port 8000 --reload

# Terminal 2 — frontend
pnpm dev
```

### Docker (both services)
```bash
docker compose up --build
# web: http://localhost:3000  · agent-api: http://localhost:8000
```

### ⚠ PYTHONPATH isolation workaround (this environment)
The Hermes desktop terminal session injects `PYTHONPATH` pointing at the
Hermes agent venv, which **contaminates** the project's Python virtualenv and
silently resolves packages (e.g. pydantic) to the wrong place. When running any
Python command for this project, **prefix it with `PYTHONPATH=`** to keep the
project venv isolated:
```bash
PYTHONPATH= .venv/Scripts/python -m pytest
PYTHONPATH= .venv/Scripts/python -m ruff check app tests
PYTHONPATH= .venv/Scripts/python -m mypy app
```
Also ensure the venv was created against a standalone Python (e.g. the uv
managed cpython), not the Hermes venv python.

## Scripts (frontend)
- `pnpm dev` / `pnpm build` / `pnpm start`
- `pnpm exec tsc --noEmit` — typecheck
- `pnpm run lint` — eslint
- `pnpm exec vitest run` — tests

## Scripts (agent service)
- `PYTHONPATH= .venv/Scripts/python -m pytest` — tests
- `PYTHONPATH= .venv/Scripts/python -m ruff check app tests` — lint
- `PYTHONPATH= .venv/Scripts/python -m mypy app` — typecheck


---

# ChatGPT Independent Full Code Audit

**Audit target:** `merqato-ai-resort-platform-audit-6d4c85e.zip`  
**Audited commit:** `6d4c85e41b26a6e4a618892cf7fc4518b4b7e615`  
**ZIP SHA-256 verified:** `056f77ad5761d6be217bc3a49105fe7eec829702ed48cff69f26a51930811b52`  
**Audit type:** Static file-by-file code audit of the uploaded ZIP, manifest, documentation, backend, frontend, fixtures, and tests.

## Executive Summary

The codebase is a real, coherent MerQato AI Resort Platform foundation. It contains the expected major layers:

- Next.js 16 App Router frontend with React 19, TypeScript, Tailwind CSS 4
- Next.js BFF route for guest agent requests
- FastAPI backend service
- CrewAI `ConciergeCrew` with YAML agent/task prompts
- OpenRouter LLM configuration
- Tenant-scoped Qdrant retrieval layer
- Supabase migration, repository abstraction, and PostgREST backend adapter
- Immutable knowledge-version model
- Audit logs and ingestion job records
- BAIA fixture data across the 10 required knowledge categories
- Backend and frontend tests

The code is not ready for BAIA public-site integration or production deployment yet. The main issue is not missing ambition; it is disconnected runtime wiring. The core pieces exist, but the production request path still does not fully use live Supabase, real embeddings, published-only Qdrant metadata, or a CrewAI Flow.

## Verified Archive Integrity

- The uploaded ZIP hash matched Hermes' reported hash.
- `FILE_MANIFEST.csv` was present.
- All listed files were present.
- File sizes and checksums matched the manifest during audit.
- No `.git`, `node_modules`, `.next`, Python virtualenv, or cache folders were included.
- Only dummy/test secret-looking strings were found in test files and placeholders. No real credentials were found in the ZIP.

## Confirmed Code Tree Areas

Important project areas present:

```text
services/agent-api/app/main.py
services/agent-api/app/api/routes.py
services/agent-api/app/services/concierge_service.py
services/agent-api/app/services/tenant_resolver.py
services/agent-api/app/services/credentials.py
services/agent-api/app/services/openrouter_validate.py
services/agent-api/app/crews/concierge/crew.py
services/agent-api/app/crews/concierge/config/agents.yaml
services/agent-api/app/crews/concierge/config/tasks.yaml
services/agent-api/app/knowledge/repository.py
services/agent-api/app/knowledge/supabase_backend.py
services/agent-api/app/knowledge/ingestion_service.py
services/agent-api/app/knowledge/qdrant_store.py
services/agent-api/app/knowledge/embeddings.py
services/agent-api/app/security/secrets.py
src/app/api/agent/route.ts
src/app/admin/*
src/components/guest/*
src/lib/data/*
supabase/migrations/0001_knowledge_ingestion_foundation.sql
fixtures/baia_resort/*
```

## What Is Intact

### 1. FastAPI

FastAPI is present and simple:

- `app/main.py` creates the app and mounts the API router.
- `/health` reports service status and OpenRouter configuration.
- `app/api/routes.py` exposes:
  - `POST /v1/concierge/message`
  - `POST /v1/openrouter/validate`

The backend currently has no knowledge-management API routes.

### 2. CrewAI

CrewAI is real, not a fake TypeScript replacement.

Present:

- `ConciergeCrew`
- CrewAI `Agent`
- CrewAI `Task`
- CrewAI `Crew`
- `Process.sequential`
- `TenantKnowledgeTool`
- YAML prompts in `agents.yaml` and `tasks.yaml`

The existing crew should be preserved. It should be wrapped by a Flow, not replaced.

### 3. OpenRouter

OpenRouter support exists in two places:

- Backend validation via `openrouter_validate.py`
- CrewAI LLM construction in `ConciergeCrew._build_llm()`

Current limitation: `CredentialsProvider` checks for a key, but the actual CrewAI LLM build still reads global settings. True per-tenant OpenRouter keys are not implemented yet.

### 4. Supabase Knowledge Foundation

The migration defines the correct foundation tables:

- `tenants`
- `tenant_knowledge_documents`
- `tenant_knowledge_versions`
- `knowledge_ingestion_jobs`
- `knowledge_audit_logs`

The migration includes:

- UUID tenant model
- exact 10-category knowledge constraint
- immutable version rows
- RLS enabled
- service-role policies
- audit table
- ingestion jobs table
- `published_at` on versions

### 5. BAIA Fixtures

The BAIA fixture set exists for all 10 categories:

- `identity`
- `rooms`
- `rates`
- `amenities`
- `policies`
- `wifi_power`
- `food_breakfast`
- `transport`
- `emergency_contacts`
- `faq`

These are suitable for draft seed data.

### 6. Next.js Frontend

The frontend is a Next.js 16 App Router application with React 19, TypeScript, and Tailwind CSS 4.

Present:

- public landing/template pages
- guest concierge UI
- owner/admin pages
- BFF route `/api/agent`
- admin middleware with temporary Basic Auth
- Supabase/dev data-store abstraction

The frontend is not yet the separate BAIA public landing-page design.

## Current Runtime Flow

Current guest flow:

```text
Guest browser
→ src/app/api/agent/route.ts
→ FastAPI POST /v1/concierge/message
→ run_concierge()
→ TenantResolver
→ ConciergeCrew
→ TenantKnowledgeTool
→ TenantQdrantStore.search()
→ OpenRouter LLM
→ safety checks
→ ConciergeResponse
```

This is the right overall shape, but several runtime pieces are still disconnected.

## Critical Findings

### Critical 1 — Supabase is not the default runtime backend

`KnowledgeRepository()` currently defaults to a shared in-memory backend in `repository.py`.

`SupabaseBackend` exists, but it is only used explicitly by the seed command. Production FastAPI requests do not automatically use live Supabase even when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` exist.

Impact:

- `TenantResolver` cannot resolve live `baia-resort` from Supabase during production guest requests.
- The Supabase seed can be correct while the live API still sees no tenant.
- This blocks real deployment.

Required fix:

- Change `_default_backend()` to select `SupabaseBackend` when Supabase env vars exist.
- Keep in-memory backend only for tests/local fallback.
- Add tests for backend selection.

### Critical 2 — No CrewAI Flow exists

The code has a sequential `ConciergeCrew`, but no `flow.py` and no CrewAI Flow runtime.

Impact:

- The platform lacks the controlled orchestration layer needed for:
  - tenant resolution
  - tenant status gating
  - retrieval preconditions
  - CrewAI execution
  - safety validation
  - escalation/approval branching
- Future multi-agent work will be harder and riskier without this layer.

Required fix:

- Add `services/agent-api/app/crews/concierge/flow.py`.
- Reuse the existing `ConciergeCrew`.
- Make FastAPI call the Flow, not the Crew directly.
- Do not add extra agents yet.

### Critical 3 — Production concierge uses fake embeddings

`concierge_service.py` directly imports and uses `FakeEmbeddingProvider`.

Impact:

- Production Qdrant retrieval would not use the real configured embedding provider.
- The code can appear to work while retrieval quality is meaningless.
- This violates the intended production safety model.

Required fix:

- Use `get_embedding_provider()` in production.
- Keep `FakeEmbeddingProvider` only for tests.
- Fail closed if production embedding config is missing.

### Critical 4 — Publish semantics are incomplete

The database has `published_at`, but the ingestion/publish path does not update it when content is indexed.

Impact:

- Qdrant can receive vectors for content that Supabase still reports as unpublished.
- Supabase and Qdrant can disagree about publication state.
- Guest safety becomes dependent on the ingestion path rather than enforceable metadata.

Required fix:

- Publishing must update `verification_status`, `published_at`, and Qdrant payload metadata consistently.
- Do not index until Supabase version state is verified and published.

### Critical 5 — Qdrant search lacks publication filtering

Qdrant payload includes:

- `tenant_id`
- `tenant_slug`
- `document_id`
- `document_version_id`
- `category`
- `version`
- `checksum`
- `verification_status`
- `guest_visible`
- `internal_only`
- text/source fields

Qdrant search filters only:

- `tenant_id`
- `guest_visible = true`
- `internal_only = false`

Impact:

- It does not independently require `verification_status = verified`.
- It does not require a published flag or `published_at`.
- It relies on the indexer to never index unsafe content.

Required fix:

- Add publication metadata to indexed payload.
- Search must filter verified + published + guest visible + non-internal.
- Only filter fields that are confirmed present in payload.

### Critical 6 — Draft/unknown tenant errors are not safely handled at the route

`run_concierge()` can raise `TenantNotResolvable`, but the FastAPI route catches only `OpenRouterNotConfigured`.

Impact:

- Draft or unknown tenant requests may produce server errors instead of a safe unavailable concierge response.
- BAIA is currently draft, so this matters immediately.

Required fix:

- Route/service should return a controlled safe response for draft/unknown/inactive tenants.
- Tests must cover draft BAIA behavior.

### Critical 7 — Admin knowledge management does not exist

There are no FastAPI routes or Next.js Admin screens for the new Supabase knowledge tables.

Missing:

- list categories
- read current version
- create immutable version
- verify
- publish
- archive/unpublish
- version history
- audit history

Impact:

- BAIA knowledge is CLI-seeded only.
- Resort owners cannot manage or approve knowledge in Admin.
- The draft → verify → publish workflow is not productized.

Required fix:

- Add secure FastAPI knowledge routes.
- Add protected Next.js BFF routes.
- Add Admin knowledge UI.
- Keep this separate from existing agent-action approvals.

### Critical 8 — Tenant slug is inconsistent

Current values include:

- Supabase tenant: `baia-resort`
- frontend default: `resort_demo`
- BFF chat fallback: `baia`

Impact:

- Frontend, backend, Supabase, and Qdrant may point at different tenants.
- Tests can pass while the product is disconnected.

Required fix:

- Use one canonical tenant slug: `baia-resort`.
- Put it in a shared config/constant rather than scattering literals.

### Critical 9 — The included public frontend is not the BAIA landing page

The Next.js frontend is a generic resort platform UI. It is not the separate BAIA public landing-page design currently in the Vite repository.

Impact:

- Connecting the platform to the public BAIA site cannot happen until the BAIA design/source is moved into this Next.js app or intentionally linked.
- Do not pretend the public BAIA site is already inside this project.

Required fix:

- After runtime foundation is corrected, migrate the BAIA public site into this Next.js application.
- Do that as a separate phase.

### Critical 10 — OpenRouter credential abstraction is only partial

`CredentialsProvider` exists, but the CrewAI LLM still reads global settings directly.

Impact:

- Per-resort OpenRouter keys are not truly supported yet.
- The code checks one abstraction but executes using another source.

Required fix:

- Pass resolved credential into the Crew/LLM build path.
- Keep environment-wide key only as first implementation if needed.
- Document tenant-key support as future until implemented.

## High-Risk Implementation Notes

### SupabaseBackend concerns

- `upsert_document()` uses an upsert pattern that may reset `current_version` to `0` during conflict merge.
- Version numbering appears to use read-max-plus-one, which can race under simultaneous edits.
- Job insert does not consistently associate `document_version_id`.
- `completed_at = "now()"` in REST payload may be treated as a literal string rather than SQL `now()`.

These should be fixed or tested before Admin concurrent editing.

### Repository/interface concerns

The repository is useful but does not yet expose all operations needed for Admin knowledge management:

- verify version
- publish version
- archive/unpublish
- list versions
- list audits
- get current version content

Add these to the repository layer instead of bypassing it directly from routes.

### Documentation concerns

Some docs imply the concierge runs zero-config. In reality:

- FastAPI must be running.
- OpenRouter must be configured for LLM answers.
- Qdrant and embeddings are needed for real knowledge retrieval.
- Supabase is not yet the runtime default.

Update docs after corrections.

## Security Audit

### Good

- No real secrets found in the ZIP.
- `.env.example` contains names/placeholders, not values.
- Service-role key is intended to stay server-side.
- Next.js middleware protects admin routes in production when configured.
- Backend redaction utilities exist.
- OpenRouter validation avoids storing the key.
- Browser-facing `/api/agent` does not expose secrets.

### Needs Correction

- Admin auth is temporary Basic Auth, not the planned passkey/session model.
- Knowledge-write routes do not exist yet, so their authorization model does not exist yet.
- Browser-to-FastAPI direct access should not become the default. Keep the BFF pattern.
- FastAPI write routes should require an internal server-to-server credential if exposed separately.

## Test Audit

Hermes reported:

- backend ruff pass
- mypy pass
- pytest 47 pass
- frontend TypeScript pass
- ESLint pass
- Vitest 6 pass
- Next build success

This audit did not rerun the full test suite because the ZIP excludes installed dependencies. The test structure is present and should be rerun after implementation changes.

Existing tests cover important pieces, but new tests are required for:

- Supabase runtime backend selection
- CrewAI Flow execution
- draft tenant safe response
- production embedding fail-closed behavior
- Admin knowledge routes
- BFF authorization
- immutable version editing
- verify-before-publish
- published-only Qdrant retrieval
- no Qdrant writes while draft/unpublished

## Correct Implementation Order

Do not merge the BAIA public site yet. Do not deploy yet.

Recommended order:

1. Wire `SupabaseBackend` as the runtime backend when Supabase env vars exist.
2. Align `baia-resort` across frontend, BFF, FastAPI, Supabase, and Qdrant.
3. Add safe handling for draft/unknown/inactive tenants.
4. Replace production fake embeddings with real provider selection and fail-closed behavior.
5. Fix publish semantics so Supabase `published_at` and Qdrant metadata agree.
6. Add Qdrant payload metadata and verified/published retrieval filtering.
7. Add the CrewAI Flow around the existing `ConciergeCrew`.
8. Add FastAPI knowledge-management routes through the repository layer.
9. Add protected Next.js BFF knowledge routes.
10. Add Admin knowledge UI for the 10 categories.
11. Add tests for every changed path.
12. Run full backend and frontend verification.
13. Only then migrate the BAIA public site into the Next.js application.
14. Only after another audit, deploy.

## Final Audit Verdict

The codebase is valid as a foundation, but it is not yet a connected product.

**Safe to continue development:** yes.  
**Safe to deploy as BAIA concierge:** no.  
**Safe to publish BAIA knowledge:** no.  
**Safe to merge with the BAIA public site now:** no.  
**Correct next step:** implement the runtime-foundation corrections above, then re-audit before site migration or deployment.
