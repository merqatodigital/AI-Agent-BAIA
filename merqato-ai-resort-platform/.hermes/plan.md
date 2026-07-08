# Plan — Close Runtime Integration Gaps (no redesign)

Branch target: `master` (clean at `9114ebe`). New branch from `master`:
`runtime-integration-gaps`.

Preserve (do NOT touch logic of): `ConciergeCrew`, OpenRouter, FastAPI core,
Next.js App Router, TS, Tailwind, Supabase schema, immutable versions, audit
logs, tenant isolation, draft→verify→publish gates, existing prompts/tools.

## Decisions (flagged for approval)
- **Admin↔FastAPI access**: add `CORSMiddleware` to FastAPI (allow origins from
  `CORS_ALLOW_ORIGINS`, default `http://localhost:3000`). Keys stay server-side;
  browser never receives service-role key. (Alternative = 8 BFF proxy routes;
  CORS is simpler and equally safe since FastAPI holds the key.)
- **Conversation store**: minimal in-process `ConversationStore` (guest msg +
  assistant reply only; no secrets/internal knowledge). Not durable — noted as
  future work. Wired into crew inputs.

## Files to change

### Backend (`services/agent-api/`)
1. `app/knowledge/repository.py`
   - `_default_backend()`: return `SupabaseBackend()` when `SUPABASE_URL` +
     `SUPABASE_SERVICE_ROLE_KEY` present; else `_InMemoryBackend()`.
2. `app/knowledge/supabase_backend.py` — verify `get_tenant_by_slug` returns
   `status` field; no change needed if already present (confirm during exec).
3. `app/services/concierge_service.py`
   - Embedder: use `get_embedding_provider()` (real, configured) instead of
     `FakeEmbeddingProvider()`; if unavailable → controlled safe response
     (fail closed, no crash, no fabrication).
   - Catch `TenantNotResolvable` → safe unavailable response (no draft content).
   - Wire `conversation_id` → `ConversationStore`.
4. `app/knowledge/qdrant_store.py`
   - Tighten `search()` filter to also require `verification_status=verified`
     and `published=true` (defense-in-depth). Add `published` to upsert payload.
5. `app/api/knowledge.py` (NEW) — `APIRouter` server-side routes:
   - `GET  /v1/knowledge/categories`            (10 categories)
   - `GET  /v1/knowledge/{cat}/version/current`
   - `POST /v1/knowledge/{cat}/versions`         (new immutable version)
   - `POST /v1/knowledge/{cat}/versions/{vid}/verify`
   - `POST /v1/knowledge/{cat}/versions/{vid}/publish`
   - `POST /v1/knowledge/{cat}/versions/{vid}/unpublish` (archive/unpublish)
   - `GET  /v1/knowledge/{cat}/versions`         (history)
   - `GET  /v1/knowledge/{cat}/audit`            (audit history)
   - All resolve tenant from `X-Tenant-Slug` header (service-role server-side).
     Responses NEVER include keys.
6. `app/main.py` — `include_router(knowledge_router)` + `CORSMiddleware`.
7. `app/crews/concierge/flow.py` (NEW) — minimal `ConciergeFlow`
   (`crewai.flow.Flow`): receive → resolve tenant → retrieve approved knowledge
   → run existing `ConciergeCrew` → safety check → response. Wraps crew; no new
   agents. Primary path stays `run_concierge`; flow is additive + tested.
8. `app/conversation/store.py` (NEW) — minimal in-process store.

### Frontend (`src/`)
9. `src/lib/data/index.ts` — `DEFAULT_RESORT_ID = "baia-resort"`.
10. `src/app/api/agent/route.ts` — default `resortId` `"baia"` → `"baia-resort"`.
11. `src/app/admin/knowledge/page.tsx` (NEW) — category list (fetch FastAPI
    `/v1/knowledge/categories`).
12. `src/app/admin/knowledge/[category]/page.tsx` (NEW) — view / edit / save-new
    version / verify / publish / version history / audit status. Client component
    calling FastAPI knowledge routes (CORS). Reuses existing admin Tailwind
    classes; NO visual redesign.
13. `src/components/admin/KnowledgeEditor.tsx` (NEW) — editor + action buttons.
14. Keep `src/app/admin/approvals` separate (agent-action approvals ≠ knowledge
    publishing).

### Tests
15. Backend `tests/`:
    - `test_backend_selection.py` — Supabase selected when env set; in-memory
      fallback otherwise.
    - `test_tenant_resolver_supabase.py` — draft rejected; active resolves from
      live/backend; internal_only blocking.
    - `test_knowledge_routes.py` — create immutable version, verify rules,
      publish rules, guest draft blocking, audit/history.
    - `test_embedder_fail_closed.py` — real provider missing → safe response.
    - `test_concierge_flow.py` — flow runs existing crew end-to-end (mocked LLM).
    - `test_conversation_store.py` — history persisted, no secrets.
16. Frontend `src/**/*.test.ts`:
    - `test/tenant-alignment.test.ts` — `DEFAULT_RESORT_ID === "baia-resort"` and
      BFF default resortId alignment.
    - `test/admin-knowledge-workflow.test.tsx` — mock fetch to FastAPI knowledge
      routes; verify view/edit/verify/publish/history/audit UI flow.

## Explicitly NOT done this phase
- No Qdrant vector writes (do not publish/embed BAIA).
- No BAIA publish.
- No visual design changes.
- No deployment.

## Verification (Step 4)
- Backend: `ruff`, `mypy`, `pytest` (all green).
- Frontend: `tsc --noEmit`, `eslint`, `vitest`, `next build` (all green).
