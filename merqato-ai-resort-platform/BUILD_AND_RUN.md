# BUILD_AND_RUN.md — MerQato AI Resort Platform

> Local setup, test, and production-build instructions. **Variable names only —
> no credential values.** All secrets are read from the environment or `.env`
> (gitignored). Never commit real keys.

## Prerequisites

- Python 3.11+ (backend uses `services/agent-api/.venv`)
- Node 20+ and pnpm (frontend)
- Optional external services (all work without them in demo mode):
  - Supabase project (Postgres + pgvector) — multi-tenant source of truth
  - Qdrant — per-tenant vector retrieval
  - OpenRouter account — LLM inference for the concierge

## 1. Backend (FastAPI + CrewAI)

```bash
cd services/agent-api

# create / use the virtualenv
python -m venv .venv
source .venv/Scripts/activate        # Windows git-bash / MSYS

# install dependencies
pip install -r requirements.txt       # or: pip install -e .

# configure (COPY .env.example -> .env and fill ONLY names shown below)
cp .env.example .env

# run
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
# health:  http://localhost:8000/health
# chat:    POST http://localhost:8000/v1/concierge/message
```

### Backend environment-variable names (values blank in repo)

```
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_DB_URL
OPENROUTER_API_KEY
OPENROUTER_BASE_URL            # default https://openrouter.ai/api/v1
OPENROUTER_MODEL               # default openai/gpt-4o-mini
QDRANT_URL
QDRANT_API_KEY
KNOWLEDGE_EMBEDDING_PROVIDER   # openai | none
KNOWLEDGE_EMBEDDING_MODEL      # text-embedding-3-small
OPENAI_API_KEY                 # required only when embedding provider = openai
ADMIN_API_TOKEN                # shared secret for the admin knowledge API
                               # (X-Admin-Token); admin routes are DISABLED
                               # (503) until this is set
TENANT_SLUG
TENANT_DOMAIN
VOICE_INTERNAL_API_KEY         # shared only with the voice service
```

Runtime backend selection: when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`
are set, the FastAPI service reads/writes live Supabase (service role).
Without them it falls back to an in-memory backend (tests / zero-config demo).
The canonical tenant slug is `baia-resort` (`DEFAULT_TENANT_SLUG` in
`app/config.py` and `src/lib/config.ts`).

## 2. Frontend (Next.js 16 App Router)

```bash
# from repo root
pnpm install

# configure (COPY .env.example -> .env.local and fill ONLY names shown below)
cp .env.example .env.local

pnpm dev        # http://localhost:3000
pnpm build      # production build (.next/)
pnpm start      # serve the production build
```

### Frontend environment-variable names (values blank in repo)

```
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY     # server-only
OPENROUTER_API_KEY            # server-only
OPENROUTER_BASE_URL
OPENROUTER_MODEL
AGENT_API_URL                 # BFF -> FastAPI target, default http://localhost:8000
VOICE_API_URL                 # BFF -> speech-to-speech, default http://localhost:8765
ADMIN_API_TOKEN               # server-only; forwarded as X-Admin-Token by the
                              # /api/admin/knowledge BFF proxy (never sent to
                              # the browser)
NEXT_PUBLIC_APP_URL
TEMP_ADMIN_USERNAME           # interim Basic Auth for /admin + /api/admin
TEMP_ADMIN_PASSWORD           # interim Basic Auth for /admin + /api/admin
```

## 3. Tests

### Backend
```bash
cd services/agent-api
source .venv/Scripts/activate
PYTHONPATH=. python -m ruff check app tests
PYTHONPATH=. python -m mypy app
PYTHONPATH=. python -m pytest -q
```

### Frontend
```bash
pnpm exec tsc --noEmit
pnpm run lint
pnpm exec vitest run
pnpm run build
```

## 4. Production build

- Backend: standard ASGI deploy (uvicorn/gunicorn behind a reverse proxy).
  Dockerfile + docker-compose.yml are provided at repo root.
- Frontend: `pnpm build` produces a standalone Next.js output
  (`next.config.ts` sets `output: "standalone"`).

## 5. Knowledge management

### Admin UI (recommended)
With both services running and `ADMIN_API_TOKEN` set on BOTH sides:
- `/admin/knowledge` — the 10 categories with draft/verified/published state
- `/admin/knowledge/<category>` — JSON draft editor (every save creates a NEW
  immutable version), verify / publish / unpublish actions, version history,
  ingestion status, audit history

The publish flow is: draft → verify → publish. Publishing sets
`published_at` in Supabase, indexes the content into the tenant's Qdrant
collection with publication metadata, and rolls back if indexing fails.
Guest retrieval only ever sees verified + published + guest-visible +
non-internal content.

### CLI seeding (fixtures)
```bash
cd services/agent-api
python -m app.scripts.seed_tenant \
    --tenant-slug baia-resort --business-name "BAIA Resort" \
    --business-type resort --fixtures-path ../../fixtures/baia_resort \
    --status draft --dry-run
# drop --dry-run to write; add --verification-status verified --publish
# ONLY after human verification and explicit approval
```

> Do **not** activate, publish or index the live BAIA tenant without explicit
> owner approval. All end-to-end proofs run against test tenants.
