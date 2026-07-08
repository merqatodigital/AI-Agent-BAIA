# TEST_RESULTS.md

All commands run on branch `claude/merqato-platform-completion-d6p01m` after
completing Milestones 1–4 (working agent runtime, safe knowledge publishing,
admin workflow, end-to-end proof). No tests were weakened, skipped, or
deleted to make verification pass; the suite grew from 47 to 95 backend tests.

## Backend (services/agent-api)
- `ruff check app tests`  -> PASS (All checks passed!)
- `mypy app`              -> PASS (Success: no issues found in 34 source files)
- `pytest -q`             -> PASS (95 passed, 0 failures)
  Warnings: CrewAI upstream DeprecationWarning
  (`function_calling_llm is deprecated`); harmless, no failures.

New coverage added in this pass:
- Supabase-vs-memory runtime backend selection (`test_backend_selection.py`)
- ConciergeFlow orchestration + conversation_id preservation (`test_flow.py`)
- Draft/suspended/archived/unknown tenant safe responses (`test_tenant_gating.py`)
- Embedding fail-closed behaviour (`test_embeddings_fail_closed.py`)
- SupabaseBackend concurrency (version race retry, non-destructive document
  upsert, real timestamps, job↔version linkage) (`test_supabase_backend.py`)
- Draft → verify → publish → unpublish lifecycle, Supabase/Qdrant consistency,
  rollback on failed indexing, published-only retrieval filters
  (`test_publishing.py`)
- Admin knowledge routes: token auth fail-closed, tenant scoping, full
  lifecycle over HTTP (`test_admin_knowledge_routes.py`)
- End-to-end proof over a test tenant: admin edit → immutable draft → verify
  → publish → Supabase publication → Qdrant indexing → audit records → guest
  question → published-knowledge retrieval → grounded CrewAI answer; plus no
  draft leakage, no internal-content leakage, no cross-tenant retrieval, and
  controlled 503s when credentials are missing (`test_e2e_proof.py`)

## Frontend (repo root, Next.js 16)
- `tsc --noEmit`          -> PASS (no type errors)
- `eslint` (pnpm run lint)-> PASS (no lint errors)
- `vitest run`            -> PASS (7 passed, 1 test file; includes the new
  `/api/admin` middleware protection test)
- `next build`            -> PASS (production build succeeded; static + dynamic routes)

## Summary
All backend and frontend verification green: 95 backend tests + 7 frontend
tests passing, lint/typecheck clean on both sides, production build succeeds.
