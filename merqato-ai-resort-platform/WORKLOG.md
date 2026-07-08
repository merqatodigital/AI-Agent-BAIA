# WORKLOG — MerQato AI Resort Platform completion

Small-loop execution log. One task per loop: inspect → implement → test → fix → log → commit.

## Milestone 1 — Working agent runtime

- [x] 1.1 Use `SupabaseBackend` for real runtime requests (env-driven backend selection; memory stays test-only)
- [x] 1.2 Standardize the tenant slug to `baia-resort` (shared constant, frontend + BFF + backend + tests)
- [x] 1.3 Replace production fake embeddings with the existing real provider (fail closed when unconfigured)
- [x] 1.4 Pass the resolved OpenRouter key into the existing CrewAI LLM
- [x] 1.5 Add a CrewAI Flow around the existing `ConciergeCrew`; FastAPI calls the Flow
- [x] 1.6 Handle draft, inactive and unknown tenants with safe responses at the route
- [x] 1.7 Preserve `conversation_id` through the flow without fake memory (echoed in ConciergeResponse, no memory attached)
- [x] 1.V Validation: ruff clean, mypy clean, pytest 67 passed; tsc clean, ESLint clean, Vitest 6 passed, next build OK

## Milestone 2 — Safe knowledge publishing

- [x] 2.1 Concurrency-safe version creation; never overwrite history
- [x] 2.2 Fix document upsert so it does not reset `current_version`
- [x] 2.3 Publish/unpublish repository operations (verified + published_at + guest_visible + !internal_only) — PublishingService
- [x] 2.4 Link ingestion jobs to the exact document version; record completed/failed correctly
- [x] 2.5 Audit records for every state change (create_draft, verify_version, publish_version, publish_failed, unpublish_version, archive_version, ingest_version)
- [x] 2.6 Publication metadata in Qdrant payload; index only on publish; remove on unpublish; rollback published_at on indexing failure
- [x] 2.7 Qdrant search filters: tenant + verified + published + guest_visible + !internal_only
- [x] 2.V Validation: ruff clean, mypy clean, pytest 84 passed; tsc clean, ESLint clean, Vitest 6 passed, next build OK

## Milestone 3 — Admin workflow

- [x] 3.1 FastAPI knowledge-management routes (list categories, current version, create draft, verify, publish, unpublish/archive, version history, audit history, ingestion status) behind X-Admin-Token (fail closed when unset)
- [ ] 3.2 Next.js BFF routes proxying the FastAPI knowledge routes (admin-protected, no keys in browser)
- [ ] 3.3 `/admin/knowledge` page (category list + status)
- [ ] 3.4 `/admin/knowledge/[category]` page (view/edit draft, verify, publish, unpublish, history, audits)
- [ ] 3.V Validation: full backend + frontend checks

## Milestone 4 — End-to-end proof

- [ ] 4.1 E2E test: admin edit → immutable draft → verify → publish → Supabase publication → Qdrant indexing → audit record → guest question → published knowledge retrieval → grounded CrewAI answer
- [ ] 4.2 Negative proofs: no draft leakage, no internal-content leakage, no cross-tenant retrieval, safe failure without credentials
- [ ] 4.V Validation: full backend + frontend checks

## Final

- [ ] F.1 Update README.md, CODE_TREE.txt, TEST_RESULTS.md, BUILD_AND_RUN.md, audit (implemented fixes)
- [ ] F.2 Secret scan
- [ ] F.3 Push branch

## Log

- 2026-07-08: Extracted `baia-aiagent.zip` into `merqato-ai-resort-platform/`. Baseline verified green: pytest 47 passed, ruff clean, mypy clean, tsc clean, Vitest 6 passed.
