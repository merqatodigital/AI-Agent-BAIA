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
TENANT_SLUG
TENANT_DOMAIN
```

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
NEXT_PUBLIC_APP_URL
TEMP_ADMIN_USERNAME           # placeholder only — auth not implemented
TEMP_ADMIN_PASSWORD           # placeholder only — auth not implemented
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

## 5. Knowledge seeding (CLI only, in this commit)

```bash
cd services/agent-api
PYTHONPATH=. python -m app.scripts.seed_tenant <tenant_slug> \
    --status draft --publish false
# publishes (indexes to Qdrant) only after verify + --publish true
```

> Do **not** publish BAIA or write to Qdrant until independent audit and human
> verification are complete.
