import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";
import { StatCard } from "@/components/admin/StatCard";

export const dynamic = "force-dynamic";

export default async function MissionControlPage() {
  const store = getDataStore();
  const data = await store.getMissionControl(DEFAULT_RESORT_ID);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Owner · Mission Control</p>
          <h1 className="mt-2 font-serif text-4xl">Today at a glance</h1>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            data.buildStatus === "ok"
              ? "bg-forest/15 text-forest"
              : "bg-danger/15 text-danger"
          }`}
        >
          Build: {data.buildStatus}
        </span>
      </div>

      <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Arrivals today" value={data.todayArrivals.length} />
        <StatCard label="Departures today" value={data.todayDepartures.length} />
        <StatCard label="Current guests" value={data.currentGuests.length} />
        <StatCard label="Open inquiries" value={data.openInquiries.length} />
        <StatCard
          label="Pending approvals"
          value={data.pendingApprovals.length}
        />
        <StatCard label="Cleaning tasks" value={data.cleaningTasks.length} />
        <StatCard label="Maintenance" value={data.maintenanceTasks.length} />
        <StatCard label="AI chats" value={data.aiChats.length} />
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        {/* Recent bookings */}
        <div className="card p-6">
          <h2 className="font-serif text-2xl">Recent bookings</h2>
          <ul className="mt-4 divide-y divide-line">
            {data.recentBookings.map((b) => (
              <li
                key={b.id}
                className="flex items-center justify-between py-3 text-sm"
              >
                <span>
                  <span className="font-medium text-ink">{b.guestName}</span> ·{" "}
                  {b.checkIn} → {b.checkOut}
                </span>
                <span className="rounded-full bg-surface px-2 py-0.5 text-xs capitalize text-muted">
                  {b.status}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* OpenRouter */}
        <div className="card p-6">
          <h2 className="font-serif text-2xl">OpenRouter status</h2>
          <p className="mt-3 text-sm text-ink/70">{data.openRouter.status}</p>
          <p className="mt-4 text-sm">
            <span className="text-muted">Configured:</span>{" "}
            <span className={data.openRouter.configured ? "text-forest" : "text-danger"}>
              {data.openRouter.configured ? "Yes" : "No"}
            </span>
          </p>
          <a
            href="/admin/openrouter"
            className="mt-5 inline-block rounded-full bg-accent px-5 py-2 text-sm font-semibold text-warmwhite no-underline transition hover:opacity-90"
          >
            Manage OpenRouter
          </a>
        </div>

        {/* AI conversations */}
        <div className="card p-6">
          <h2 className="font-serif text-2xl">AI conversations</h2>
          <ul className="mt-4 space-y-3">
            {data.aiChats.map((c) => (
              <li key={c.id} className="rounded-xl bg-surface/50 p-3 text-sm">
                <p className="font-medium text-ink">{c.guestName}</p>
                <p className="text-ink/70">“{c.message}”</p>
                <p className="mt-1 text-muted">→ {c.response}</p>
                {c.escalated && (
                  <span className="mt-1 inline-block rounded-full bg-bronze/20 px-2 py-0.5 text-xs text-bronze">
                    Escalated
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>

        {/* Activity */}
        <div className="card p-6">
          <h2 className="font-serif text-2xl">Latest activity</h2>
          <ul className="mt-4 space-y-2 text-sm text-ink/70">
            {data.recentActivity.map((a) => (
              <li key={a.id} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                {a.label}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
