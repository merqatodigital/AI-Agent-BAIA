# TALA Voice Service

This isolated service runs Hugging Face `speech-to-speech` as TALA's realtime
audio layer:

```text
browser WebRTC -> Silero VAD -> Faster Whisper -> TALA CrewAI -> Kokoro TTS
```

TALA's existing FastAPI/CrewAI concierge remains the only agent brain. The
voice service calls its protected, OpenAI-compatible
`POST /v1/chat/completions` adapter. It does not call OpenRouter directly and
does not duplicate resort rules, knowledge retrieval, or safety policy.

## Run with the platform

From `merqato-ai-resort-platform/`:

```bash
docker compose --profile voice up --build
```

Then open `http://localhost:3000/concierge` and select **Talk to TALA**.
The first start downloads the speech models and can take several minutes.

## Runtime settings

- `VOICE_INTERNAL_API_KEY` — shared only with `agent-api`; required outside development.
- `VOICE_NUM_PIPELINES` — simultaneous calls; each pipeline loads its own models.
- `VOICE_DEVICE` — `cpu` by default; use `cuda` on a compatible host.
- `VOICE_STT_MODEL` — `small.en` by default.
- `VOICE_STT_COMPUTE_TYPE` — `int8` by default for CPU.
- `TALA_VOICE` — Kokoro voice, default `af_heart`.
- `SPEECH_TO_SPEECH_ICE_SERVERS` — JSON STUN/TURN configuration for production WebRTC.

The initial profile is English-first. Faster Whisper can later be switched to
a multilingual checkpoint when Tagalog voice input is part of the rollout.

## Production note

Do not expose the raw speech-to-speech HTTP/WebSocket port without a gateway.
The upstream server does not provide its own authentication or throttling.
Use a protected signaling gateway, rate limits, TLS, and TURN for public use.
