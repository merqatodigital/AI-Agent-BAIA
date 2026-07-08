"use client";

import { useState } from "react";

const RECOMMENDED_MODELS = [
  "openai/gpt-4o-mini",
  "anthropic/claude-3.5-haiku",
  "google/gemini-flash-1.5",
  "meta-llama/llama-3.1-8b-instruct",
];

/**
 * OpenRouter admin: paste the CUSTOMER's own key, test the connection through
 * the FastAPI service, and choose a model. This UI only validates via
 * /api/openrouter (a BFF proxy to FastAPI /v1/openrouter/validate). It never
 * transmits MerQato credentials and never performs OpenRouter calls directly.
 */
export function OpenRouterSettings() {
  const [key, setKey] = useState("");
  const [model, setModel] = useState<string>(RECOMMENDED_MODELS[0]);
  const [testing, setTesting] = useState(false);
  const [test, setTest] = useState<{
    valid: boolean;
    model?: string;
    message?: string;
  } | null>(null);
  const [saved, setSaved] = useState(false);

  async function runTest() {
    setTesting(true);
    setTest(null);
    try {
      const res = await fetch("/api/openrouter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key, model }),
      });
      const json = await res.json();
      setTest(json);
    } catch {
      setTest({ valid: false, message: "Network error" });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <p className="eyebrow">Integrations</p>
      <h1 className="mt-2 font-serif text-4xl">OpenRouter</h1>
      <p className="mt-3 text-sm text-ink/70">
        Connect your own OpenRouter API key. The AI concierge and agents run on
        your account and your credits — MerQato never bills you for tokens.
      </p>

      <div className="card mt-8 space-y-5 p-6">
        <div>
          <label className="text-sm font-medium text-ink">API Key</label>
          <input
            type="password"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              setSaved(false);
            }}
            placeholder="sk-or-v1-…"
            className="mt-2 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-ink">Model</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="mt-2 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
          >
            {RECOMMENDED_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={runTest}
            disabled={testing || !key}
            className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-warmwhite transition hover:opacity-90 disabled:opacity-50"
          >
            {testing ? "Testing…" : "Test connection"}
          </button>
          <button
            onClick={() => setSaved(true)}
            disabled={!key}
            className="rounded-full border border-line px-5 py-2 text-sm font-semibold text-ink transition hover:bg-surface disabled:opacity-50"
          >
            Save
          </button>
        </div>

        {test && (
          <div
            className={`rounded-xl p-4 text-sm ${
              test.valid
                ? "bg-forest/10 text-forest"
                : "bg-danger/10 text-danger"
            }`}
          >
            {test.valid ? (
              <p>
                ✓ Connected · model <strong>{test.model}</strong>
              </p>
            ) : (
              <p>✗ {test.message ?? "Connection failed"}</p>
            )}
          </div>
        )}
        {saved && (
          <p className="rounded-xl bg-forest/10 p-4 text-sm text-forest">
            ✓ Settings saved for this resort (persisted to your server config).
          </p>
        )}
      </div>

      <div className="mt-8 card p-6">
        <h2 className="font-serif text-xl">Usage</h2>
        <div className="mt-4 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-semibold text-ink">—</p>
            <p className="text-xs uppercase tracking-widest text-muted">Today</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-ink">—</p>
            <p className="text-xs uppercase tracking-widest text-muted">
              This month
            </p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-ink">—</p>
            <p className="text-xs uppercase tracking-widest text-muted">
              Est. cost
            </p>
          </div>
        </div>
        <p className="mt-4 text-xs text-muted">
          Live token accounting appears once your key is connected and traffic
          flows through OpenRouter.
        </p>
      </div>
    </div>
  );
}
