"use client";

import { useState } from "react";

/**
 * Guest AI Concierge widget. Sends the message to /api/agent, which is a BFF
 * proxy to the FastAPI + CrewAI concierge service. If OpenRouter is not
 * configured, the backend returns a controlled error (never a fabricated
 * answer). This component does not contain any agent logic.
 */
export function ConciergeWidget() {
  const [messages, setMessages] = useState<
    { role: "guest" | "host"; text: string; requiresApproval?: boolean; escalationReason?: string | null }[]
  >([{ role: "host", text: "Hello! I'm your MerQato concierge. Ask me about rooms, tours, dining, or transport." }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setMessages((m) => [...m, { role: "guest", text }]);
    setInput("");
    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const json = await res.json().catch(() => null);
      const reply =
        json?.reply ??
        "Sorry — I couldn't reach the concierge just now. Please try again.";
      setMessages((m) => [
        ...m,
        {
          role: "host",
          text: reply,
          requiresApproval: Boolean(json?.requires_approval),
          escalationReason: json?.escalation_reason ?? null,
        },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "host",
          text: "I'm having trouble connecting. Please try again.",
          escalationReason: "connection_error",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card flex h-[480px] max-w-md flex-col p-0">
      <div className="rounded-t-2xl bg-accent px-5 py-4 text-warmwhite">
        <p className="eyebrow text-warmwhite/70">AI Concierge</p>
        <p className="font-serif text-xl">Ask anything about your stay</p>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={m.role === "guest" ? "text-right" : "text-left"}
          >
            <span
              className={`inline-block max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                m.role === "guest"
                  ? "bg-ink text-warmwhite"
                  : "bg-surface text-ink"
              }`}
            >
              {m.text}
            </span>
          </div>
        ))}
        {busy && (
          <p className="text-left text-xs text-muted">Concierge is typing…</p>
        )}
      </div>
      <form
        className="flex gap-2 border-t border-line p-4"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. What time is breakfast?"
          className="flex-1 rounded-full border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-full bg-accent px-5 py-2 text-sm font-semibold text-warmwhite transition hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
