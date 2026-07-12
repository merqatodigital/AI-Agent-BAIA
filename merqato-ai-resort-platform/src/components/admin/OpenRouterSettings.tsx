"use client";

import { useEffect, useState } from "react";

type RuntimeMode = "openrouter" | "ollama" | "hermes";
type HermesProvider = "openrouter" | "ollama";

type ProviderSettings = {
  mode: RuntimeMode;
  openrouter_configured: boolean;
  openrouter_key_masked?: string | null;
  openrouter_model: string;
  ollama_base_url: string;
  ollama_model: string;
  hermes_provider: HermesProvider;
};

type OpenRouterModel = {
  id: string;
  name: string;
  is_free: boolean;
  context_length?: number | null;
};

const DEFAULTS: ProviderSettings = {
  mode: "openrouter",
  openrouter_configured: false,
  openrouter_model: "openai/gpt-4o-mini",
  ollama_base_url: "http://localhost:11434",
  ollama_model: "qwen2.5:3b",
  hermes_provider: "openrouter",
};

export function OpenRouterSettings() {
  const [settings, setSettings] = useState<ProviderSettings>(DEFAULTS);
  const [apiKey, setApiKey] = useState("");
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>([]);
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

  async function loadOpenRouterModels() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch("/api/admin/ai-provider", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "list_openrouter_models",
          api_key: apiKey || null,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? json.detail ?? "Unable to load OpenRouter models");
      const models = Array.isArray(json.models) ? json.models : [];
      setOpenRouterModels(models);
      if (models.length && !models.some((model: OpenRouterModel) => model.id === settings.openrouter_model)) {
        setSettings((current) => ({ ...current, openrouter_model: models[0].id }));
      }
      setMessage(`Loaded ${models.length} OpenRouter models, including free and paid options.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load OpenRouter models");
    } finally {
      setBusy(false);
    }
  }

  async function testOpenRouter() {
    if (!apiKey && !settings.openrouter_configured) {
      setError("Enter or save an OpenRouter key before testing.");
      return;
    }
    if (!apiKey) {
      setMessage("Saved OpenRouter key is configured. Load models to verify it.");
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
          hermes_provider: settings.hermes_provider,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error ?? json.detail ?? "Save failed");
      setSettings(json);
      setApiKey("");
      setMessage("AI runtime settings saved securely.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const runtimeOptions: Array<{ value: RuntimeMode; title: string; description: string }> = [
    {
      value: "openrouter",
      title: "OpenRouter",
      description: "Use any available OpenRouter model directly. Free and paid models are supported.",
    },
    {
      value: "ollama",
      title: "Local Ollama",
      description: "Use a model installed on the machine running the FastAPI service.",
    },
    {
      value: "hermes",
      title: "Hermes Agent",
      description: "Enable BAIA's hospitality agent, knowledge tools, routing, and human escalation.",
    },
  ];

  return (
    <div className="max-w-4xl">
      <p className="eyebrow">Integrations</p>
      <h1 className="mt-2 font-serif text-4xl">AI Runtime</h1>
      <p className="mt-3 text-sm text-ink/70">
        Choose a direct model provider or enable Hermes as the full BAIA hospitality agent.
      </p>

      <div className="card mt-8 space-y-6 p-6">
        <div className="grid gap-3 md:grid-cols-3">
          {runtimeOptions.map((option) => (
            <button
              type="button"
              key={option.value}
              onClick={() => setSettings({ ...settings, mode: option.value })}
              className={`rounded-2xl border p-5 text-left transition ${
                settings.mode === option.value ? "border-accent bg-accent/5" : "border-line"
              }`}
            >
              <span className="font-serif text-xl">{option.title}</span>
              <span className="mt-2 block text-sm text-muted">{option.description}</span>
            </button>
          ))}
        </div>

        <section className="rounded-2xl border border-line p-5">
          <h2 className="font-serif text-xl">OpenRouter models</h2>
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
          {openRouterModels.length ? (
            <select
              value={settings.openrouter_model}
              onChange={(event) => setSettings({ ...settings, openrouter_model: event.target.value })}
              className="mt-3 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
            >
              {openRouterModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.is_free ? "FREE · " : "PAID · "}{model.name}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={settings.openrouter_model}
              onChange={(event) => setSettings({ ...settings, openrouter_model: event.target.value })}
              className="mt-3 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
              placeholder="openai/gpt-4o-mini"
            />
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            <button onClick={loadOpenRouterModels} disabled={busy || (!apiKey && !settings.openrouter_configured)} className="rounded-full border border-line px-5 py-2 text-sm font-semibold disabled:opacity-50">
              Load all models
            </button>
            <button onClick={testOpenRouter} disabled={busy || (!apiKey && !settings.openrouter_configured)} className="rounded-full border border-line px-5 py-2 text-sm font-semibold disabled:opacity-50">
              Test OpenRouter
            </button>
          </div>
        </section>

        <section className="rounded-2xl border border-line p-5">
          <h2 className="font-serif text-xl">Local Ollama models</h2>
          <p className="mt-1 text-sm text-muted">
            Detects models installed on the same machine or network as the FastAPI service.
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
            Detect installed models
          </button>
        </section>

        {settings.mode === "hermes" && (
          <section className="rounded-2xl border border-accent bg-accent/5 p-5">
            <h2 className="font-serif text-xl">Hermes Agent</h2>
            <p className="mt-1 text-sm text-muted">
              Hermes adds BAIA hospitality behavior, verified knowledge retrieval, intent routing, and human escalation. Choose the model provider Hermes will use.
            </p>
            <select
              value={settings.hermes_provider}
              onChange={(event) => setSettings({ ...settings, hermes_provider: event.target.value as HermesProvider })}
              className="mt-4 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm"
            >
              <option value="openrouter">Hermes powered by OpenRouter</option>
              <option value="ollama">Hermes powered by local Ollama</option>
            </select>
          </section>
        )}

        {message && <p className="rounded-xl bg-forest/10 p-4 text-sm text-forest">✓ {message}</p>}
        {error && <p className="rounded-xl bg-danger/10 p-4 text-sm text-danger">✗ {error}</p>}

        <button onClick={saveSettings} disabled={busy} className="rounded-full bg-accent px-6 py-2 text-sm font-semibold text-warmwhite disabled:opacity-50">
          {busy ? "Working…" : "Save AI runtime settings"}
        </button>
      </div>
    </div>
  );
}
