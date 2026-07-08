# HERMES_AUDIT.md — MerQato AI Resort Platform

> Audit snapshot of the codebase at commit `6d4c85e` on branch `master`.
> Generated for independent file-by-file review (ChatGPT). No code was changed
> for this packaging step. BAIA remains `draft` and **unpublished**; no Qdrant
> vectors were created for it.

## 1. Project purpose and goal

MerQato AI Resort Platform is a multi-tenant, agent-driven resort website + AI
concierge. Each resort (tenant) gets a branded Next.js site and an AI
Concierge (CrewAI + OpenRouter) that answers guest questions using **only**
that tenant's verified, published knowledge. Knowledge is authored in Supabase,
versioned immutably, verified by a human, then published to a per-tenant Qdrant
vector collection for retrieval. The design enforces strict tenant isolation
and fail-closed guest safety (draft / internal / unpublished knowledge can
never reach a guest).

The repository also contains a separate foundation demo (`DevDataStore`,
`resort_demo`) so the UI runs with zero configuration. This demo is clearly
labeled and is **not** the multi-tenant production path.

## 2. Current architecture

```
Browser (Next.js 16 App Router, React 19, TS, Tailwind 4)
  ├─ Guest Concierge  → /api/agent (BFF) → FastAPI /v1/concierge/message
  └─ Admin            → /api/* (BFF) + future direct FastAPI /v1/knowledge/*
FastAPI (Python)  app/main.py
  ├─ ConciergeService → CrewAI ConciergeCrew (OpenRouter LLM)
  │     └─ TenantKnowledgeTool → Qdrant (per-tenant collection)
  ├─ TenantResolver → KnowledgeRepository → SupabaseBackend (live) | InMemory
  └─ Knowledge ingestion (CLI seed_tenant.py) → Supabase tables → (publish) Qdrant
Supabase (Postgres + pgvector): tenants, documents, immutable versions,
  ingestion_jobs, audit_logs. Service-role key used server-side only.
Qdrant: per-tenant vector collection `merqato_tenant_<slug>` for retrieval.
```

## 3. Exact runtime request flow (guest question)

1. `src/components/guest/ConciergeChat.tsx` posts `{message, resortId}` to `/api/agent`.
2. `src/app/api/agent/route.ts` (BFF, no keys) forwards to
   `AGENT_API_URL + /v1/concierge/message` (default `http://localhost:8000`).
3. `app/api/routes.py::concierge_message` → `run_concierge(ConciergeRequest)`.
4. `app/services/concierge_service.py`:
   a. `get_credentials_provider().get_openrouter_key(resort_id)` — if empty →
      raise `OpenRouterNotConfigured` → FastAPI **503** (no fabricated answer).
   b. `_resolve_tenant(resort_id)` → `TenantResolver.resolve_by_slug`. Only
      `status=active` tenants resolve; **draft/suspended/archived are rejected**.
   c. Build `ConciergeCrew(ctx, TenantKnowledgeTool)` and `crew.kickoff`.
   d. `TenantKnowledgeTool._run` embeds the query and calls
      `TenantQdrantStore.search()` (filtered to this tenant +
      `guest_visible=true`, `internal_only=false`).
   e. LLM answers from retrieved chunks only (constrained by `agents.yaml` /
      `tasks.yaml`).
   f. `detect_forbidden` + `detect_escalation` set `requires_approval` /
      `escalation_reason`.
5. `ConciergeResponse` returned unchanged through the BFF to the browser.

## 4. CrewAI Flow steps

There is **no CrewAI `@flow` layer yet** (see §13, Known gaps). The active
orchestration is the sequential `ConciergeCrew` (`Process.sequential`):
`receive question → resolve tenant (server-side) → retrieve approved knowledge
(TenantKnowledgeTool) → run concierge crew → safety check → return response`.
A planned minimal `ConciergeFlow` is described in `.hermes/plan.md` but is
**not implemented** in this commit.

## 5. How the existing ConciergeCrew is reused

`app/crews/concierge/crew.py::ConciergeCrew` is a `@CrewBase` with one
`@agent` (`concierge_agent`) and one `@task` (`concierge_task`). Agent/task
instructions come from `config/agents.yaml` + `config/tasks.yaml` (no keys).
The LLM (`crewai.LLM`, provider `openrouter`) is injected at runtime from
`Settings.openrouter_*`. The only tool is `TenantKnowledgeTool`, constructed
from a verified `TenantContext` (collection name fixed server-side). The crew
is built and kicked off inside `concierge_service.run_concierge`. It is the
single production agent engine — no duplicate agents.

## 6. FastAPI routes

- `GET  /health` → `HealthResponse` (status, crewai_version, environment,
  openrouter_configured).
- `POST /v1/concierge/message` → `ConciergeResponse`.
- `POST /v1/openrouter/validate` → validates a **transient** customer key
  (never stored/returned; errors redacted).
- Knowledge-management REST routes are **NOT present yet** (CLI-only via
  `seed_tenant.py`). Planned in `.hermes/plan.md`.

## 7. Next.js BFF routes (`src/app/api/`)

- `/api/agent` → proxy to FastAPI `/v1/concierge/message`.
- `/api/openrouter` → proxy to FastAPI `/v1/openrouter/validate`.
- `/api/resort` → resort profile CRUD (Supabase `resort_profile` or Dev store).
- `/api/inquiry` → guest inquiries.
- `/api/mission-control` → ops dashboard data.
- All BFF routes hold no keys and forward nothing secret to the browser.

## 8. Admin authorization flow

The frontend `src/app/admin/*` pages (dashboard, resort editor, OpenRouter
settings, approvals) are **not gated by authentication in this commit** —
`TEMP_ADMIN_USERNAME` / `TEMP_ADMIN_PASSWORD` exist only as blank
placeholders in `.env.example`. This is a known gap (§13). The "Approvals"
screen is for **agent-action approvals** (bookings, pricing, posts), which is
**distinct** from knowledge verify/publish.

## 9. Supabase runtime-selection flow

`app/knowledge/repository.py::_default_backend()` currently returns the
**in-memory** `_InMemoryBackend` whenever no explicit backend is supplied
(`seed_tenant.py` passes `SupabaseBackend` explicitly). `SupabaseBackend`
(`app/knowledge/supabase_backend.py`) exists and is used by the seed CLI, but
is **not yet the default at request time**. Planned fix: select
`SupabaseBackend` when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are present.

## 10. Immutable draft → verify → publish flow

1. `seed_tenant.py` (or a future Admin UI) calls `IngestionService.ingest_fixture_dict`.
2. Content is canonicalized; a SHA-256 checksum is computed. Duplicate
   checksums are skipped (idempotent).
3. A logical `tenant_knowledge_documents` row exists per `(tenant, category)`.
4. A new immutable `tenant_knowledge_versions` row is inserted (version = N+1,
   never updated in place).
5. `verification_status` ∈ {draft, verified, rejected, archived}.
6. Embedding/indexing in Qdrant happens **only** when
   `_is_indexable(status, guest_visible, internal_only)` AND `publish=True`
   (i.e. `verified` + `guest_visible` + `not internal_only` + publish).
7. An `audit_logs` row is written for every ingest/verify/publish action.
8. BAIA was seeded with `status=draft`, `publish=false` → **never indexed**
   (0 Qdrant vectors).

## 11. Tenant-isolation controls

- `TenantResolver` requires a verified backend lookup; only `ACTIVE` tenants
  serve guest retrieval (fail-closed).
- `TenantQdrantStore` uses a deterministic, server-generated collection name
  `merqato_tenant_<normalized_slug>`; there is **no cross-tenant search method**
  and the collection name is never client-supplied.
- `search()` filters `tenant_id` in payload (defense-in-depth) plus
  `guest_visible=true`, `internal_only=false`.
- `KnowledgeRepository` keys everything by `tenant_id`; Supabase RLS is enabled
  on all five tables.

## 12. OpenRouter behavior

- Client: `app/services/openrouter_validate.py` (urllib, no SDK) for key
  validation; `crewai.LLM(provider="openrouter", api_key=...)` for inference.
- Env: `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`
  (default `openai/gpt-4o-mini`).
- **No automatic fallback.** Missing key → `OpenRouterNotConfigured` → 503.
- Per-tenant key design (`CredentialsProvider`) is an abstract future extension;
  only `EnvCredentialsProvider` exists today.

## 13. Known stubs, dead code, fallbacks, disconnected paths

- **`app/knowledge/sample_repository.py`** — LEGACY `SampleKnowledgeRepository`,
  explicitly marked "NOT ON THE ACTIVE CONCIERGE PATH"; dead code.
- **In-memory default backend** — `repository._default_backend()` returns
  in-memory, so runtime tenant resolution is not yet live-Supabase.
- **Frontend `DEFAULT_RESORT_ID = "resort_demo"`** (`src/lib/data/index.ts`) —
  disconnected from the real `baia-resort` tenant in Supabase.
- **No Admin knowledge UI** — verify/publish is CLI-only; `admin/approvals` is
  for agent actions, not knowledge publishing.
- **`FakeEmbeddingProvider` in `concierge_service.py:78`** — guest retrieval
  uses fake embeddings unless `OPENAI_API_KEY` + `KNOWLEDGE_EMBEDDING_PROVIDER=openai`
  are set. With BAIA draft (0 Qdrant vectors) it returns "(no tenant knowledge found)".
- **No CrewAI Flow layer** — sequential crew only.
- **No conversation memory** — `conversation_id` is threaded but unused
  server-side (stateless per request).
- **No FastAPI CORS / knowledge REST routes** — BFF proxy is the only bridge.
- **No admin authentication** — `TEMP_ADMIN_*` are blank placeholders.
- **Deprecation warnings** — CrewAI logs `function_calling_llm is deprecated`
  (upstream noise; tests pass).

## 14. Embedding-provider behavior

- `app/knowledge/embeddings.py`: `EmbeddingProvider` ABC with
  `OpenAIEmbeddingProvider` (real, requires `OPENAI_API_KEY`) and
  `FakeEmbeddingProvider` (deterministic test double, 1536-dim).
- `get_embedding_provider()` returns OpenAI when
  `KNOWLEDGE_EMBEDDING_PROVIDER=openai`, else raises.
- Production path must use the real provider **only when env vars exist**; if
  unavailable it must fail closed (return a safe unavailable response), never
  fabricate. `FakeEmbeddingProvider` is for tests only.

## 15. Qdrant read/write behavior

- Write: `TenantQdrantStore.upsert_chunks` (called only by the publish step of
  `IngestionService`). Each point carries a full payload incl. `tenant_id`,
  `document_version_id`, `category`, `verification_status`, `guest_visible`,
  `internal_only`, `chunk_index`, `text`.
- Read: `search()` embeds the query and queries the per-tenant collection with
  the tenant + `guest_visible` + `internal_only` filter.
- **No vectors were written for BAIA in this commit** (draft, publish=false).

## 16. Guest-safety gates (summary proof)

A guest answer can only include tenant knowledge when **all** hold:
- tenant `status = active` (resolver rejects draft/suspended/archived)
- version `verification_status = verified`
- version `published_at is not null` (publish step)
- version `guest_visible = true`
- version `internal_only = false`

Plus the agent is instructed (YAML) to answer **only** from retrieved knowledge
and never to confirm bookings, issue refunds, charge, change prices, publish,
delete, or promise availability. Forbidden-phrase + escalation detection
(`app/agents/safety.py`) forces `requires_approval` / escalation. Before a
tenant is active+published, the chat returns a safe unavailable response and
exposes **zero** draft content.

## 17. Remaining work before deployment / connecting public BAIA site

1. Wire `SupabaseBackend` as the runtime default backend (live tenant resolution).
2. Align frontend `DEFAULT_RESORT_ID` to `baia-resort` (single source of truth).
3. Add FastAPI knowledge REST routes (list/read/version/verify/publish/
   unpublish/history/audit) — server-side, never return the service-role key.
4. Build Admin knowledge UI (view/edit/save-version/verify/publish/history/
   audit), separate from agent-action approvals.
5. Replace fake embeddings in the runtime path with a configurable real provider;
   fail closed if unavailable. Keep `FakeEmbeddingProvider` for tests only.
6. (Optional) Add a minimal CrewAI Flow wrapping the existing crew.
7. Wire `conversation_id` into a minimal server-side conversation store (or
   document why stateless).
8. Add admin authentication before any public exposure.
9. Activate BAIA tenant (`status=active`) and publish its 10 verified categories
   **only after** independent audit + human verification.
10. Run the full verification suite (this ZIP) on every change.
