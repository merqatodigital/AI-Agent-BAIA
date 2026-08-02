# TALA Resort-in-a-Box — Product and Technical Stack

TALA is sold as a **24/7 Digital Manager**, not as a website theme. BAIA is the
first complete tenant and the reference implementation for future resorts.

## 1. Storefront — convert visitors into warm leads

| Capability | Technical foundation |
| --- | --- |
| Mobile resort website | Next.js 16, React 19, Tailwind 4, Vercel-compatible deployment |
| TALA text concierge | `/api/agent` BFF -> FastAPI -> CrewAI ConciergeFlow |
| TALA voice concierge | Browser WebRTC -> Hugging Face speech-to-speech -> TALA adapter |
| Lead capture | Next.js BFF -> Supabase `leads` with tenant RLS |
| Quote handoff | Approval-gated workflow; owner sends or approves the final quote |
| Conversion tracking | First-party events stored by tenant; optional analytics adapter |

TALA can ask for email or WhatsApp only when it is relevant to the guest's
request. Contact details need explicit consent, a retention policy, and an
owner-visible deletion path.

## 2. Digital Concierge — the property-specific brain

```text
Guest text/voice
  -> tenant and credential gate
  -> TALA ConciergeFlow
  -> published resort knowledge (Supabase + Qdrant)
  -> safety and approval policy
  -> answer, lead, or human escalation
```

Core stack:

- FastAPI + CrewAI Flow for orchestration and tools.
- OpenRouter-compatible LLM, using each resort's own key and model setting.
- Supabase Postgres as the multi-tenant source of truth.
- Qdrant for verified, published, guest-visible knowledge retrieval.
- Hugging Face speech-to-speech for VAD, STT, turn-taking, interruption, and TTS.
- WebRTC for live browser voice; text remains available when voice is offline.
- Approval gates for bookings, prices, refunds, payments, and published content.

Future channels use adapters around the same TALA core:

- WhatsApp text and voice notes through the official WhatsApp Business API.
- Telephone calls through a telephony provider when a resort chooses to pay for it.
- PMS/calendar adapters: iCal first, then Cloudbeds/Sirvoy integrations where API access is available.

## 3. Command Center — simple owner operations

| Module | Data and workflow |
| --- | --- |
| Leads | Contact, stay dates, party size, intent, source, consent, status, owner |
| Booking pipeline | Inquiry -> quote -> approval -> booked/lost; never auto-confirmed by AI |
| Property settings | Rooms, rates, policies, amenities, blackout dates, voice and tone |
| Conversations | Text transcript, voice transcript, channel, escalation, outcome |
| Upsells | Breakfast, transfers, excursions, accepted/declined value |
| Operations | Tasks, housekeeping, maintenance, supplier expenses, receipt images |
| Analytics | Response load, frequent questions, lead conversion, upsell revenue |

Supabase Auth controls staff access. PostgreSQL RLS isolates every resort. The
service role stays server-side; guests never receive admin or provider keys.

## Multi-tenant product boundary

Every business record carries `tenant_id`. A sellable tenant contains:

- domain and brand theme;
- published property knowledge and local guide;
- model/provider credentials;
- TALA tone, voice, and channel settings;
- staff roles and approval rules;
- leads, conversations, tasks, expenses, and audit history.

One codebase serves all tenants. Resort data and secrets do not get copied into
the frontend or into per-customer forks.

## Delivery sequence

1. **BAIA proof:** live text + voice TALA, verified knowledge, controlled handoff.
2. **Lead engine:** consented contact capture, pipeline, notifications, transcripts.
3. **Booking safety:** availability/PMS adapter and owner approval workflow.
4. **Revenue layer:** breakfast, transfer, and excursion recommendations with attribution.
5. **Operations:** tasks, expenses, receipt capture, cash-flow summaries.
6. **Template onboarding:** domain, brand, knowledge import, test, owner approval, publish.

## Commercial packaging

- **Setup fee:** site branding, custom domain, knowledge preparation, TALA tone,
  staff onboarding, testing, and launch.
- **Monthly manager plan:** hosting, command center, updates, monitoring, and a
  clearly stated usage allowance for voice/LLM services.
- **Pass-through or customer-owned usage:** keep provider costs visible and
  predictable; never promise unlimited voice when compute costs scale per call.
