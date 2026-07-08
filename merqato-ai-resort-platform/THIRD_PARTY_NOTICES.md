# Third-Party Software Notices

This project incorporates or depends on third-party open-source software.
Licenses and attributions are reproduced below as required by their respective
licenses.

---

## CrewAI — MIT License

**Version used:** `crewai` **1.15.1** (Python package, installed from PyPI into
`services/agent-api`).

CrewAI is the actual agent-orchestration framework used by the FastAPI agent
service (`services/agent-api`). The Next.js frontend contains **no** agent logic
of its own; it proxies to the FastAPI service, which constructs real
`crewai.Agent`, `crewai.Task`, and `crewai.Crew` objects.

**License:** MIT

> Copyright (c) 2023-2025 CrewAI Inc.
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

**Source:** https://github.com/crewAIInc/crewAI

---

## Other notable dependencies (summary)

| Package | Version (pinned) | License |
| --- | --- | --- |
| fastapi | 0.139.0 | MIT |
| uvicorn | (resolved) | BSD-3-Clause |
| pydantic | 2.12.5 | MIT |
| pydantic-settings | (resolved) | MIT |
| portalocker | 2.7.0 | MIT/PSF |
| pywin32 | 311 | PSF |
| pytest | (resolved) | MIT |
| httpx | (resolved) | BSD-3-Clause |
| ruff | (resolved) | MIT |
| mypy | (resolved) | MIT |

Full license texts for these packages are available in their respective
repositories and distributions.

---

## Frontend (Next.js) third-party licenses

The Next.js application (`next`, `react`, `tailwindcss`, `shadcn/ui` components,
`framer-motion`, `supabase-js`, `vitest`) carries its own license notices, which
are reproduced in each package's distribution under `node_modules/` and at the
upstream project repositories. This file focuses on the agent service, which is
the only component that uses third-party agent-orchestration code (CrewAI).
