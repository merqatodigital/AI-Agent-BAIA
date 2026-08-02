# ROADMAP — MerQato AI Resort Website

Autonomous build loop. Each item checked when its feature is production-quality
(typecheck + lint + tests + build all green, verified at runtime).

## Status legend
- [x] done & verified  [~] partial  [ ] todo

## Build order (from spec)
1. [x] Project scaffold — Next.js 16 + TS + Tailwind 4 (pnpm)
2. [x] Brand system — KAPWA palette/typography, Logo SVG, globals.css @theme
3. [~] Authentication — Supabase Auth adapter scaffolded in data layer; login UI pending
4. [x] Admin dashboard — shell + Mission Control + Resort Editor + Approvals + OpenRouter
5. [x] Resort editor — every field editable, PATCH /api/resort
6. [x] Knowledge base — interface + dev adapter (keyword search) + pgvector adapter
7. [x] AI Concierge — /concierge page + widget + agent runner (KB→OpenRouter→safety)
8. [x] OpenRouter integration — real client, test key, model select, usage fields, env-only key
9. [x] Booking inquiry workflow — form + API + pending-approval (never auto-confirm)
10. [x] Mission Control — arrivals/departures/guests/inquiries/approvals/tasks/chats/analytics
11. [~] Staff operations — tasks model + housekeeping/maintenance agents create tasks (UI grid pending)
12. [ ] Analytics — live dashboard (currently static snapshot in Mission Control)
13. [ ] Blog — CMS + Marketing Agent drafting (types + approval flow exist)
14. [ ] Marketing Agent — UI to generate/review posts
15. [ ] Revenue Agent — UI to suggest pricing/packages
16. [~] Voice Concierge — Hugging Face speech-to-speech + WebRTC + Faster Whisper + Kokoro integrated; production gateway/TURN and load tests pending
17. [ ] Multi-resort support — DataStore is per-resort; admin multi-tenant UI pending
18. [ ] Production optimization — bundle/perf audit
19. [ ] Documentation — deploy + template docs
20. [ ] Commercial packaging — clone template → import → publish flow

## Latest cycle (verified)
- Fixed agent safety matcher (forbidden-action detection now catches "confirm my
  booking" via all-significant-words presence). Tests 6/6 pass.
- Added dedicated /concierge page matching the KAPWA AI Concierge mockup
  (split hero + chat, suggested questions, Popular Topics rail, For Guests/Team
  grids, footer stats).
- Runtime smoke test: /, /concierge, /admin = 200; inquiry POST=201;
  mission-control + agent endpoints return real data; no-key demo mode graceful.
- CSS @import ordering fixed (fonts import precedes tailwind).

## Next highest-priority unfinished task
Supabase schema (supabase/schema.sql) + auth login UI, then staff-ops UI grid,
then analytics/blog/marketing/revenue UIs.
