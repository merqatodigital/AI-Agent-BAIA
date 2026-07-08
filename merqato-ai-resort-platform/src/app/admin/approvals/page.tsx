import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";

export const dynamic = "force-dynamic";

export default async function ApprovalsPage() {
  const store = getDataStore();
  const approvals = await store.listApprovals(DEFAULT_RESORT_ID);

  return (
    <div className="max-w-3xl">
      <p className="eyebrow">Human in the loop</p>
      <h1 className="mt-2 font-serif text-4xl">Approvals</h1>
      <p className="mt-3 text-sm text-ink/70">
        The AI never confirms bookings, changes prices, publishes posts, or
        charges cards. Every sensitive action waits here for your sign-off.
      </p>

      <ul className="mt-8 space-y-3">
        {approvals.map((a) => (
          <li key={a.id} className="card p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-serif text-xl text-ink">{a.action}</p>
                <p className="mt-1 text-sm text-ink/70">{a.description}</p>
                <p className="mt-2 text-xs uppercase tracking-widest text-muted">
                  Requested by {a.requestedBy}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${
                  a.status === "pending"
                    ? "bg-bronze/20 text-bronze"
                    : a.status === "approved"
                      ? "bg-forest/15 text-forest"
                      : "bg-danger/15 text-danger"
                }`}
              >
                {a.status}
              </span>
            </div>
          </li>
        ))}
        {approvals.length === 0 && (
          <li className="card p-6 text-center text-sm text-muted">
            No pending approvals. The AI is standing by.
          </li>
        )}
      </ul>
    </div>
  );
}
