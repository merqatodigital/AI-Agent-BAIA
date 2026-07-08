"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

/**
 * Admin knowledge workflow UI (draft → verify → publish → unpublish).
 * All requests go through the protected BFF (/api/admin/knowledge/*); no
 * tokens or tenant identifiers live in browser code.
 */

type CategorySummary = {
  category: string;
  document_id: string | null;
  current_version: number;
  verification_status: string | null;
  published: boolean;
  published_at: string | null;
};

type VersionRow = {
  id: string;
  version: number;
  verification_status: string;
  guest_visible: boolean;
  internal_only: boolean;
  published_at: string | null;
  created_at?: string;
  content: Record<string, unknown>;
};

type AuditRow = {
  id: string;
  action: string;
  actor_type: string;
  actor_id: string | null;
  document_version_id: string | null;
  created_at?: string;
};

type JobRow = {
  id: string;
  status: string;
  source: string;
  chunks_created: number;
  error_message: string | null;
  document_version_id: string | null;
};

const CATEGORY_LABELS: Record<string, string> = {
  identity: "Identity",
  rooms: "Rooms",
  rates: "Rates",
  amenities: "Amenities",
  policies: "Policies",
  wifi_power: "Wi-Fi & Power",
  food_breakfast: "Food & Breakfast",
  transport: "Transport",
  emergency_contacts: "Emergency Contacts",
  faq: "FAQ",
};

function StatusChip({
  status,
  published,
}: {
  status: string | null;
  published: boolean;
}) {
  if (published) {
    return (
      <span className="rounded-full bg-forest/15 px-3 py-1 text-xs font-semibold text-forest">
        Published
      </span>
    );
  }
  if (!status) {
    return (
      <span className="rounded-full bg-surface px-3 py-1 text-xs font-semibold text-muted">
        No content
      </span>
    );
  }
  const cls =
    status === "verified"
      ? "bg-bronze/20 text-bronze"
      : status === "draft"
        ? "bg-surface text-muted"
        : "bg-danger/15 text-danger";
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${cls}`}>
      {status}
    </span>
  );
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/admin/knowledge/${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail =
      (data && (data.detail || data.error)) || `request failed (${res.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

/* ------------------------------------------------------------------------- */
/* Category overview (/admin/knowledge)                                       */
/* ------------------------------------------------------------------------- */
export function KnowledgeCategoryList() {
  const [categories, setCategories] = useState<CategorySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<CategorySummary[]>("categories")
      .then(setCategories)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="card mt-8 p-6 text-sm text-danger">
        Could not load knowledge state: {error}
      </div>
    );
  }
  if (!categories) {
    return <div className="card mt-8 p-6 text-sm text-muted">Loading…</div>;
  }

  return (
    <ul className="mt-8 grid gap-3 sm:grid-cols-2">
      {categories.map((c) => (
        <li key={c.category} className="card p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Link
                href={`/admin/knowledge/${c.category}`}
                className="font-serif text-xl text-ink no-underline hover:text-accent"
              >
                {CATEGORY_LABELS[c.category] ?? c.category}
              </Link>
              <p className="mt-1 text-xs uppercase tracking-widest text-muted">
                {c.current_version > 0
                  ? `Version ${c.current_version}`
                  : "Not created yet"}
              </p>
            </div>
            <StatusChip status={c.verification_status} published={c.published} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------------- */
/* Category manager (/admin/knowledge/[category])                             */
/* ------------------------------------------------------------------------- */
export function KnowledgeCategoryManager({ category }: { category: string }) {
  const [current, setCurrent] = useState<VersionRow | null>(null);
  const [versions, setVersions] = useState<VersionRow[]>([]);
  const [audits, setAudits] = useState<AuditRow[]>([]);
  const [jobs, setJobs] = useState<JobRow[]>([]);
  const [draftText, setDraftText] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [vs, as, js] = await Promise.all([
        api<VersionRow[]>(`${category}/versions`),
        api<AuditRow[]>(`${category}/audits`),
        api<JobRow[]>(`jobs`),
      ]);
      setError(null);
      setVersions(vs);
      setAudits(as);
      setJobs(js);
      try {
        const cur = await api<{ version: VersionRow | null }>(
          `${category}/current`,
        );
        setCurrent(cur.version);
        if (cur.version) {
          setDraftText(JSON.stringify(cur.version.content, null, 2));
        }
      } catch {
        setCurrent(null); // no document yet — start from an empty editor
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }, [category]);

  useEffect(() => {
    queueMicrotask(() => void reload());
  }, [reload]);

  async function run(label: string, fn: () => Promise<unknown>) {
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      await fn();
      setNotice(`${label} succeeded`);
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  function saveDraft() {
    let content: unknown;
    try {
      content = JSON.parse(draftText);
    } catch {
      setError("Draft must be valid JSON");
      return;
    }
    void run("Create draft", () =>
      api(`${category}/draft`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    );
  }

  const act = (versionId: string, action: "verify" | "publish" | "unpublish", body = {}) =>
    run(action, () =>
      api(`versions/${versionId}/${action}`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    );

  return (
    <div className="space-y-8">
      {(error || notice) && (
        <div
          className={`card p-4 text-sm ${error ? "text-danger" : "text-forest"}`}
        >
          {error ?? notice}
        </div>
      )}

      {/* Current version + lifecycle actions */}
      <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-serif text-2xl">Current version</h2>
          {current ? (
            <StatusChip
              status={current.verification_status}
              published={Boolean(current.published_at)}
            />
          ) : (
            <StatusChip status={null} published={false} />
          )}
        </div>
        {current && (
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-ink/70">
            <span>Version {current.version}</span>
            {current.published_at && <span>· published {current.published_at}</span>}
            <span className="flex flex-wrap gap-2">
              {current.verification_status === "draft" && (
                <ActionButton
                  label="Verify"
                  busy={busy}
                  onClick={() => act(current.id, "verify")}
                />
              )}
              {current.verification_status === "verified" &&
                !current.published_at && (
                  <ActionButton
                    label="Publish"
                    busy={busy}
                    onClick={() => act(current.id, "publish")}
                  />
                )}
              {current.published_at && (
                <ActionButton
                  label="Unpublish"
                  busy={busy}
                  onClick={() => act(current.id, "unpublish")}
                />
              )}
            </span>
          </div>
        )}

        <h3 className="mt-6 text-sm font-medium text-ink">
          Edit as JSON (creates a NEW immutable draft version)
        </h3>
        <textarea
          rows={12}
          spellCheck={false}
          className="mt-2 w-full rounded-xl border border-line bg-bg px-4 py-3 font-mono text-xs outline-none focus:border-accent"
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          placeholder='{ "summary": "…" }'
        />
        <div className="mt-3">
          <ActionButton label="Create draft" busy={busy} onClick={saveDraft} />
        </div>
      </section>

      {/* Version history */}
      <section className="card p-6">
        <h2 className="font-serif text-2xl">Version history</h2>
        <ul className="mt-4 divide-y divide-line">
          {versions.map((v) => (
            <li
              key={v.id}
              className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
            >
              <span>
                <span className="font-medium text-ink">v{v.version}</span>
                {v.internal_only && (
                  <span className="ml-2 text-xs text-muted">internal</span>
                )}
              </span>
              <span className="flex items-center gap-2">
                <StatusChip
                  status={v.verification_status}
                  published={Boolean(v.published_at)}
                />
                {v.verification_status === "draft" && (
                  <ActionButton
                    small
                    label="Verify"
                    busy={busy}
                    onClick={() => act(v.id, "verify")}
                  />
                )}
                {v.verification_status === "verified" && !v.published_at && (
                  <ActionButton
                    small
                    label="Publish"
                    busy={busy}
                    onClick={() => act(v.id, "publish")}
                  />
                )}
                {v.published_at && (
                  <ActionButton
                    small
                    label="Unpublish"
                    busy={busy}
                    onClick={() => act(v.id, "unpublish")}
                  />
                )}
              </span>
            </li>
          ))}
          {versions.length === 0 && (
            <li className="py-3 text-sm text-muted">No versions yet.</li>
          )}
        </ul>
      </section>

      {/* Ingestion status */}
      <section className="card p-6">
        <h2 className="font-serif text-2xl">Ingestion status</h2>
        <ul className="mt-4 divide-y divide-line">
          {jobs.slice(0, 8).map((j) => (
            <li key={j.id} className="flex items-center justify-between py-2 text-sm">
              <span className="text-ink/70">
                {j.source}
                {j.chunks_created > 0 && ` · ${j.chunks_created} chunks`}
                {j.error_message && (
                  <span className="text-danger"> · {j.error_message}</span>
                )}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs capitalize ${
                  j.status === "completed"
                    ? "bg-forest/15 text-forest"
                    : j.status === "failed"
                      ? "bg-danger/15 text-danger"
                      : "bg-surface text-muted"
                }`}
              >
                {j.status}
              </span>
            </li>
          ))}
          {jobs.length === 0 && (
            <li className="py-2 text-sm text-muted">No ingestion jobs yet.</li>
          )}
        </ul>
      </section>

      {/* Audit history */}
      <section className="card p-6">
        <h2 className="font-serif text-2xl">Audit history</h2>
        <ul className="mt-4 space-y-2 text-sm text-ink/70">
          {audits.slice(0, 12).map((a) => (
            <li key={a.id} className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              <span className="capitalize">{a.action.replaceAll("_", " ")}</span>
              <span className="text-muted">
                by {a.actor_id ?? a.actor_type}
                {a.created_at ? ` · ${a.created_at}` : ""}
              </span>
            </li>
          ))}
          {audits.length === 0 && (
            <li className="text-muted">No audit records yet.</li>
          )}
        </ul>
      </section>
    </div>
  );
}

function ActionButton({
  label,
  busy,
  onClick,
  small = false,
}: {
  label: string;
  busy: string | null;
  onClick: () => void;
  small?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy !== null}
      className={`rounded-full bg-accent font-semibold text-warmwhite transition hover:opacity-90 disabled:opacity-50 ${
        small ? "px-4 py-1 text-xs" : "px-6 py-2.5 text-sm"
      }`}
    >
      {busy === label || busy?.toLowerCase() === label.toLowerCase()
        ? "Working…"
        : label}
    </button>
  );
}
