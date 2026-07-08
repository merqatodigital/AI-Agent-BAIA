"use client";

import { useState } from "react";
import type { ResortProfile } from "@/lib/types";

/**
 * Editable resort profile form. Persists via /api/resort (PATCH).
 * Everything here is owner-editable — no hardcoded business data.
 */
export function ResortEditor({ profile }: { profile: ResortProfile }) {
  const [form, setForm] = useState<ResortProfile>(profile);
  const [status, setStatus] = useState<"idle" | "saving" | "done">("idle");

  function set<K extends keyof ResortProfile>(key: K, value: ResortProfile[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function save() {
    setStatus("saving");
    await fetch("/api/resort", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setStatus("done");
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Resort name">
          <input
            className={inputCls}
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </Field>
        <Field label="Tagline">
          <input
            className={inputCls}
            value={form.tagline}
            onChange={(e) => set("tagline", e.target.value)}
          />
        </Field>
        <Field label="Location">
          <input
            className={inputCls}
            value={form.location}
            onChange={(e) => set("location", e.target.value)}
          />
        </Field>
        <Field label="Hero image URL">
          <input
            className={inputCls}
            value={form.heroImageUrl}
            onChange={(e) => set("heroImageUrl", e.target.value)}
          />
        </Field>
        <Field label="Contact email">
          <input
            className={inputCls}
            value={form.contactEmail}
            onChange={(e) => set("contactEmail", e.target.value)}
          />
        </Field>
        <Field label="Contact phone">
          <input
            className={inputCls}
            value={form.contactPhone}
            onChange={(e) => set("contactPhone", e.target.value)}
          />
        </Field>
      </div>

      <Field label="Description">
        <textarea
          rows={3}
          className={inputCls}
          value={form.description}
          onChange={(e) => set("description", e.target.value)}
        />
      </Field>

      <Field label="Amenities (comma separated)">
        <input
          className={inputCls}
          value={form.amenities.join(", ")}
          onChange={(e) =>
            set(
              "amenities",
              e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
            )
          }
        />
      </Field>

      <Field label="Policies">
        <textarea
          rows={3}
          className={inputCls}
          value={form.policies}
          onChange={(e) => set("policies", e.target.value)}
        />
      </Field>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={status === "saving"}
          className="rounded-full bg-accent px-6 py-2.5 text-sm font-semibold text-warmwhite transition hover:opacity-90 disabled:opacity-50"
        >
          {status === "saving" ? "Saving…" : "Save changes"}
        </button>
        {status === "done" && (
          <span className="text-sm text-forest">✓ Saved</span>
        )}
      </div>
    </div>
  );
}

const inputCls =
  "mt-1 w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-ink">{label}</span>
      {children}
    </label>
  );
}
