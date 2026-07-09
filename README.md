# AI-Agent-BAIA

**MerQato's AI concierge & knowledge-publishing platform for Palawan resorts.**

AI-Agent-BAIA turns a resort's operational knowledge — rooms, rates, policies, local attractions, FAQs — into a polished, mobile-first guest website with a built-in **AI concierge** that answers guests in natural language. It's the flagship product of **MerQato**, an AI-operator marketplace built for businesses across Palawan.

[![Live site](https://img.shields.io/badge/live-BAIA%20San%20Vicente-435347?logo=vercel&logoColor=white)](https://baia-san-vicente-palawan-island.vercel.app)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/Agent%20API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tailwind](https://img.shields.io/badge/Styles-Tailwind%204-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

👉 **[Live demo → BAIA Beachfront Boutique Lodge](https://baia-san-vicente-palawan-island.vercel.app)**

---

## Why it exists

Non-technical resort operators in Palawan spend hours answering the same guest questions and maintaining static websites that go stale. BAIA bundles three things into one operators can actually run:

- a **luxury, mobile-first website** — rooms, amenities, and curated local experiences;
- a **live AI concierge** guests can chat with, trained on the resort's own knowledge;
- a **knowledge backend** operators fill in once and publish everywhere.

The same engine is the template for MerQato's broader **AI-operator marketplace** — sellable AI operations for Palawan businesses.

## What's inside

| Layer | Stack | Location |
|-------|-------|----------|
| Guest website + admin | Next.js 16 · React 19 · Tailwind 4 (KAPWA design system) | [`merqato-ai-resort-platform/`](merqato-ai-resort-platform/) |
| Agent API (concierge + knowledge) | Python · FastAPI · CrewAI · Qdrant / Supabase | [`merqato-ai-resort-platform/services/agent-api/`](merqato-ai-resort-platform/services/agent-api/) |
| Tenant knowledge packs | JSON fixtures (BAIA + reusable template) | [`merqato-ai-resort-platform/fixtures/`](merqato-ai-resort-platform/fixtures/) |

Full architecture: [`merqato-ai-resort-platform/README.md`](merqato-ai-resort-platform/README.md).
Build / run / test: [`merqato-ai-resort-platform/BUILD_AND_RUN.md`](merqato-ai-resort-platform/BUILD_AND_RUN.md).

## Quick start

```bash
cd merqato-ai-resort-platform
pnpm install
pnpm dev
```

- Frontend (guest site + admin): `http://localhost:3000`
- Agent API docs: `http://localhost:8000/docs`

## Repository structure

```
AI-Agent-BAIA/
├─ README.md                      # this file
├─ LICENSE                        # MIT
├─ vercel.json                    # deploys frontend from the sub-app
├─ merqato-ai-resort-platform/    # the full application
│  ├─ src/                        # Next.js app (guest site + admin console)
│  ├─ services/agent-api/         # Python FastAPI agent + knowledge service
│  ├─ fixtures/                   # tenant knowledge packs (JSON)
│  ├─ docs/                       # deployment & architecture docs
│  └─ package.json
└─ baia-aiagent.zip               # original source archive (provenance)
```

## Deploy

The frontend deploys to **Vercel** straight from this repo via the included
[`vercel.json`](vercel.json) (root → `merqato-ai-resort-platform/`). See
[`merqato-ai-resort-platform/docs/DEPLOYMENT.md`](merqato-ai-resort-platform/docs/DEPLOYMENT.md)
for environment variables and the agent service.

## License

Released under the [MIT License](LICENSE).

## Contact

**MerQato** · San Vicente, Palawan, Philippines
🔗 Live site: <https://baia-san-vicente-palawan-island.vercel.app>
