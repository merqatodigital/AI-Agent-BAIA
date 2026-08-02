"use client";

import { useRef, useState } from "react";
import type { SuggestedQuestion, PopularTopic } from "@/lib/concierge-ui";
import { useTalaVoice, type TalaVoiceStatus } from "./useTalaVoice";

/**
 * Public AI Concierge chat — mirrors the KAPWA "AI Concierge" mockup:
 * greeting, suggested-question bubbles, a Popular Topics rail, and a live
 * chat against /api/agent (a BFF proxy to the FastAPI + CrewAI service).
 *
 * This component does not contain any agent logic and never fabricates
 * answers. It displays the server's reply, and surfaces approval-required
 * and escalation states returned by the backend.
 */

type HostMessage = {
  role: "host";
  text: string;
  requiresApproval?: boolean;
  escalationReason?: string | null;
};

type ChatMessage = { role: "guest"; text: string } | HostMessage;

const GREETING: HostMessage = {
  role: "host",
  text: "Hi! I'm TALA, your digital concierge. Ask me anything about your stay, our resort, San Vicente, or Palawan.",
};

const VOICE_STATUS: Record<TalaVoiceStatus, string> = {
  idle: "Voice is ready",
  connecting: "Connecting to TALA…",
  listening: "TALA is listening",
  "user-speaking": "Listening to you…",
  thinking: "TALA is thinking…",
  speaking: "TALA is speaking",
  error: "Voice needs attention",
};

export function ConciergeChat({
  suggested,
  popularTopics,
}: {
  suggested: SuggestedQuestion[];
  popularTopics: PopularTopic[];
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);
  const voice = useTalaVoice({
    audioRef,
    onUserTranscript: (text) => {
      setMessages((current) => [...current, { role: "guest", text }]);
    },
    onAssistantTranscript: (text) => {
      setMessages((current) => [...current, { role: "host", text }]);
    },
  });
  const voiceActive = !["idle", "error"].includes(voice.status);

  async function send(text: string) {
    const msg = text.trim();
    if (!msg || busy) return;
    setBusy(true);
    setMessages((m) => [...m, { role: "guest", text: msg }]);
    setInput("");
    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const json = await res.json().catch(() => null);
      // Use the backend contract directly. No fabrication: if the backend
      // did not return a reply, show an honest connection message.
      const reply: HostMessage = json?.reply
        ? {
            role: "host",
            text: json.reply,
            requiresApproval: Boolean(json.requires_approval),
            escalationReason: json.escalation_reason ?? null,
          }
        : {
            role: "host",
            text: "I'm having trouble connecting to the concierge right now. Please try again shortly.",
            escalationReason: "connection_error",
          };
      setMessages((m) => [...m, reply]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "host",
          text: "I'm having trouble connecting to the concierge right now. Please try again shortly.",
          escalationReason: "connection_error",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card flex h-[560px] w-full flex-col overflow-hidden">
      <div className="flex items-center gap-3 bg-accent px-5 py-4 text-warmwhite">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-warmwhite/70 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-warmwhite" />
        </span>
        <div>
          <p className="font-serif text-xl leading-none">TALA Concierge</p>
          <p className="text-xs text-warmwhite/70">Online · 24/7</p>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat */}
        <div className="flex flex-1 flex-col">
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
                      : m.requiresApproval
                        ? "border border-amber-400/60 bg-amber-50 text-ink"
                        : "bg-surface text-ink"
                  }`}
                >
                  {m.text}
                  {m.role === "host" && m.requiresApproval && (
                    <span className="mt-2 block text-xs font-semibold text-amber-700">
                      Needs staff approval before any action is taken.
                    </span>
                  )}
                  {m.role === "host" &&
                    m.escalationReason &&
                    !m.escalationReason.includes("connection_error") && (
                      <span className="mt-1 block text-xs text-muted">
                        Escalated: {m.escalationReason}
                      </span>
                    )}
                </span>
              </div>
            ))}
            {busy && <p className="text-xs text-muted">Concierge is typing…</p>}
            {messages.length <= 1 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {suggested.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => send(s.text)}
                    className="rounded-full border border-line bg-bg px-3 py-1.5 text-xs text-ink transition hover:bg-surface"
                  >
                    {s.text}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-line bg-surface/30 px-4 py-2">
            <span className="flex min-w-0 items-center gap-2 text-xs text-muted">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${
                  voiceActive ? "animate-pulse bg-forest" : "bg-line"
                }`}
              />
              <span className="truncate">
                {voice.error ?? VOICE_STATUS[voice.status]}
              </span>
            </span>
            {voice.supported && (
              <button
                type="button"
                onClick={voiceActive ? voice.stop : voice.start}
                disabled={voice.status === "connecting"}
                className={`shrink-0 rounded-full px-4 py-2 text-xs font-semibold transition disabled:opacity-50 ${
                  voiceActive
                    ? "border border-line bg-bg text-ink hover:bg-surface"
                    : "bg-forest text-warmwhite hover:opacity-90"
                }`}
              >
                {voiceActive ? "End voice" : "Talk to TALA"}
              </button>
            )}
            <audio ref={audioRef} autoPlay className="hidden" />
          </div>
          <form
            className="flex gap-2 border-t border-line p-4"
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your question..."
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

        {/* Popular topics rail */}
        <aside className="hidden w-44 flex-col gap-2 border-l border-line bg-surface/30 p-4 sm:flex">
          <p className="eyebrow">Popular Topics</p>
          {popularTopics.map((t) => (
            <button
              key={t.id}
              onClick={() => send(`Tell me about: ${t.label}`)}
              className="rounded-xl bg-bg px-3 py-2 text-left text-sm text-ink/80 transition hover:bg-warmwhite"
            >
              {t.label}
            </button>
          ))}
        </aside>
      </div>
    </div>
  );
}
