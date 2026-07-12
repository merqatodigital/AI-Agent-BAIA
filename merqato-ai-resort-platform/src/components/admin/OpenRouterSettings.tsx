"use client";

import { useEffect, useState } from "react";

type ProviderMode = "automatic" | "openrouter" | "ollama";

type ProviderSettings = {
  mode: ProviderMode;
  openrouter_configured: boolean;
  openrouter_key_masked?: string | null;
  openrouter_model: string;
  ollama_base_url: string;
  ollama_model: string;
  allow_fallback: boolean;
};

const OPENROUTER_MODELS = [
  "openai/gpt-4o-mini",
  "anthropic/claude-3.5-haiku",
  "google/gemini-flash-1.5",
  "meta-llama/llama-3.1-8b-instruct",
];

const DEFAULTS: ProviderSettings = {
  mode: "automatic",
  openrouter_configured: false,
  openrouter_model: OPENROUTER_MODELS[0],
  ollama_base_url: "http://localhost:11434",
  ollama_model: "qwen2.5:3b",
  allow_fallback: false,
};

export function OpenRouterSettings() {
  const [settings, setSettings] = useState<ProviderSettings>(DEFAULTS);
  const [apiKey, setApiKey] = useState("");
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const res = await fetch("/api/admin/ai-provider", { cache: "no-store" });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? json.detail ?? "Unable to load settings");
      setSettings(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load settings");
    }
  }

  async function testOpenRouter() {
    if (!apiKey) {
      setError("Enter an OpenRouter key before testing.");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/openrouter", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey, model: settings.openrouter_model }),
      });
      const json = await res.json();
      if (!res.ok || !json.valid) throw new Error(json.message ?? "Connection failed");
      setMessage(`OpenRouter connected with ${json.model ?? settings.openrouter_model}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  async function detectOllama() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/ai-provider", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "detect_ollama",
          base_url: settings.ollama_base_url,
        }),
      });
      const json = await res.json();
      if (!res.ok || !json.available) throw new Error(json.message ?? json.detail ?? "Ollama not detected");
      const models = Array.isArray(json.models) ? json.models : [];
      setOllamaModels(models);
      if (models.length && !models.includes(settings.ollama_model)) {
        setSettings((current) => ({ ...current, ollama_model: models[0] }));
      }
      setMessage(json.message);
    } catch (err) {
      setOllamaModels([]);
      setError(err instanceof Error ? err.message : "Ollama not detected");
    } finally {
      setBusy(false);
    }
  }

  async function saveSettings() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/ai-provider", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: settings.mode,
          openrouter_api_key: apiKey || null,
          openrouter_model: settings.openrouter_model,
          ollama_base_url: settings.ollama_base_url,
          ollama_model: settings.ollama_model,
          allow_fallback: settings.allow_fallback,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? json.detail ?? "Save failed");
      setSettings(json);
      setApiKey("");
      setMessage("AI provider settings saved securely.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Integrations</p>
      <h1 className="mt-2 font-serif text-4xl">AI Provider</h1>
      <p className="mt-3 text-sm text-ink/70">
        Use OpenRouter in hosted production, Ollama on a machine that runs the agent service,
        or Automatic mode with an explicit fallback.
      </p>

      <div className="card mt-8 space-y-6 p-6">
        <div>
          <label className="text-sm font-medium text-ink">Provider mode</label>
          <select
            value={settings.mode}
            onChange={(event) => setSettings({ ...settings, mode: event.target.value as ProviderMode })}
            className="mt-2 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
          >
            <option value="automatic">Automatic</option>
            <option value="openrouter">OpenRouter only</option>
            <option value="ollama">Ollama only</option>
          </select>
        </div>

        <section className="rounded-2xl border border-line p-5">
          <h2 className="font-serif text-xl">OpenRouter</h2>
          <p className="mt-1 text-sm text-muted">
            Status: {settings.openrouter_configured ? `Configured (${settings.openrouter_key_masked})` : "Not configured"}
          </p>
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={settings.openrouter_configured ? "Enter a new key to replace the saved key" : "sk-or-v1-…"}
            className="mt-4 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
          />
          <select
            value={settings.openrouter_model}
            onChange={(event) => setSettings({ ...settings, openrouter_model: event.target.value })}
            className="mt-3 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
          >
            {OPENROUTER_MODELS.map((model) => <option key={model}>{model}</option>)}
          </select>
          <button onClick={testOpenRouter} disabled={busy || !apiKey} className="mt-4 rounded-full border border-line px-5 py-2 text-sm font-semibold disabled:opacity-50">
            Test OpenRouter
          </button>
        </section>

        <section className="rounded-2xl border border-line p-5">
          <h2 className="font-serif text-xl">Local Ollama</h2>
          <p className="mt-1 text-sm text-muted">
            Ollama must be reachable from the same machine or network as the FastAPI agent service.
          </p>
          <input
            value={settings.ollama_base_url}
            onChange={(event) => setSettings({ ...settings, ollama_base_url: event.target.value })}
            className="mt-4 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
          />
          {ollamaModels.length ? (
            <select
              value={settings.ollama_model}
              onChange={(event) => setSettings({ ...settings, ollama_model: event.target.value })}
              className="mt-3 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
            >
              {ollamaModels.map((model) => <option key={model}>{model}</option>)}
            </select>
          ) : (
            <input
              value={settings.ollama_model}
              onChange={(event) => setSettings({ ...settings, ollama_model: event.target.value })}
              className="mt-3 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
              placeholder="qwen2.5:3b"
            />
          )}
          <button onClick={detectOllama} disabled={busy} className="mt-4 rounded-full border border-line px-5 py-2 text-sm font-semibold disabled:opacity-50">
            Detect Ollama models
          </button>
        </section>

        <label className="flex items-center gap-3 text-sm text-ink">
          <input
            type="checkbox"
            checked={settings.allow_fallback}
            onChange={(event) => setSettings({ ...settings, allow_fallback: event.target.checked })}
          />
          Allow fallback to the other configured provider
        </label>

        {message && <p className="rounded-xl bg-forest/10 p-4 text-sm text-forest">✓ {message}</p>}
        {error && <p className="rounded-xl bg-danger/10 p-4 text-sm text-danger">✗ {error}</p>}

        <button onClick={saveSettings} disabled={busy} className="rounded-full bg-accent px-6 py-2 text-sm font-semibold text-warmwhite disabled:opacity-50">
          {busy ? "Working…" : "Save AI provider settings"}
        </button>
      </div>
    </div>
  );
}
