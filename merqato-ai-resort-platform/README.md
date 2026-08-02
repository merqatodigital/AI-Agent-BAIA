# MerQato AI Resort Website

A commercial, AI-powered website platform for small resorts, boutique hotels,
villas and homestays. Each customer gets a complete luxury website with an
integrated AI concierge, admin dashboard, owner Mission Control, staff
operations, and human-approval workflows.

## Stack
- Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 — public site, guest concierge UI, admin & Mission Control
- **FastAPI (Python) + the actual CrewAI framework** — dedicated agent service (`services/agent-api`). This is the *only* production agent engine.
- **Hugging Face speech-to-speech** — optional isolated WebRTC voice runtime (`services/voice-api`) with Faster Whisper STT and Kokoro TTS; TALA/CrewAI remains the brain.
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

FastAPI + real CrewAI. Guest requests run through a CrewAI **Flow**
(`ConciergeFlow`) that orchestrates: credentials gate → tenant resolution
(fail closed for draft/suspended/archived/unknown tenants) → the existing
`ConciergeCrew` (real `crewai.Agent`/`Task`/`Crew` against OpenRouter with the
resolved key) → safety validation. OpenRouter keys are never exposed to the
browser, logs, or API responses.

Production runtime flow:

```text
Next.js BFF (/api/agent)
→ FastAPI POST /v1/concierge/message
→ ConciergeFlow (CrewAI Flow)
→ tenant resolution (Supabase-backed, fail closed)
→ ConciergeCrew (existing crew, real CrewAI)
→ TenantKnowledgeTool → Qdrant (verified+published+guest-visible only)
→ safety checks
→ ConciergeResponse (conversation_id echoed untouched)
```

Endpoints:
- `GET /health` → `{status, crewai_version, environment, openrouter_configured}`
- `POST /v1/concierge/message` →
  `{reply, intent, confidence, sources, proposed_actions, requires_approval, escalation_reason, conversation_id}`
- `/v1/admin/tenants/{slug}/knowledge/*` — admin knowledge management
  (categories, current, versions, audits, jobs, draft, verify, publish,
  unpublish). Server-to-server only: requires the `X-Admin-Token` shared
  secret (`ADMIN_API_TOKEN`); disabled (503) until configured.

## Knowledge publishing (draft → verify → publish)

Resort knowledge lives in Supabase as **immutable versions** per category
(10 fixed categories). The Admin UI (`/admin/knowledge`) drives the
lifecycle; every state change writes an audit record:

1. **Draft** — every edit creates a NEW version row; history is never edited.
2. **Verify** — human approval; drafts can never reach guests.
3. **Publish** — sets `published_at` in Supabase, then indexes into the
   tenant's Qdrant collection with publication metadata. If indexing fails,
   the publication is rolled back — Supabase and Qdrant never disagree
   silently. Publishing a new version retires the previous one.
4. **Unpublish/Archive** — clears `published_at` and removes the vectors.

Guest retrieval filters Qdrant on tenant + `verification_status=verified` +
`published=true` + `guest_visible=true` + `internal_only=false`. The
canonical tenant slug is `baia-resort` (shared constant in `app/config.py`
and `src/lib/config.ts`).

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

### Docker with TALA voice

```bash
docker compose --profile voice up --build
# web: http://localhost:3000 · voice signaling: internal via /api/voice/calls
```

The first voice start downloads speech models. The voice service is isolated
from `agent-api` so Torch/audio dependencies cannot destabilize the working
CrewAI concierge. See `services/voice-api/README.md`.

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
- `PYTHONPATH= .venv/Scripts/python -m pytest` — tests (Windows; on Linux/macOS use `.venv/bin/python`)
- `PYTHONPATH= .venv/Scripts/python -m ruff check app tests` — lint
- `PYTHONPATH= .venv/Scripts/python -m mypy app` — typecheck

## Audit status

The independent audit lives in `CHATGPT_AUDIT.md`. All of its critical
findings have been implemented on this branch — see the
"Implementation status addendum" at the top of that file. Current
verification: 95 backend tests, 7 frontend tests, lint/typecheck clean,
production build green (`TEST_RESULTS.md`). The BAIA public-site migration
and live BAIA publishing remain intentionally out of scope pending owner
approval. The audit copy formerly appended to this README now lives solely
in `CHATGPT_AUDIT.md`.
