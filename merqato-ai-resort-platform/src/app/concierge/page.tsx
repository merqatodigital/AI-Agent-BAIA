import Link from "next/link";
import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";
import { SUGGESTED_QUESTIONS, POPULAR_TOPICS } from "@/lib/concierge-ui";
import { ConciergeChat } from "@/components/guest/ConciergeChat";

export const dynamic = "force-dynamic";

const GUEST_FEATURES = [
  { title: "Resort Information", desc: "Rooms, amenities, and policies at your fingertips.", cta: "Explore" },
  { title: "San Vicente Guide", desc: "Beaches, cafés, and hidden spots nearby.", cta: "Explore" },
  { title: "Transportation", desc: "Airport transfers and local routes.", cta: "Open" },
  { title: "Special Requests", desc: "Dietary needs, celebrations, and more.", cta: "Submit request" },
];

const TEAM_FEATURES = [
  { title: "Task Assistant", desc: "Housekeeping and maintenance tickets.", cta: "Manage" },
  { title: "Guest Inquiries", desc: "Every question, routed and tracked.", cta: "View" },
  { title: "Knowledge Base", desc: "Curated, searchable resort answers.", cta: "Open" },
  { title: "Analytics", desc: "Questions, satisfaction, and load.", cta: "View reports" },
];

export default async function ConciergePage() {
  const store = getDataStore();
  const profile = await store.getResortProfile(DEFAULT_RESORT_ID);

  return (
    <div>
      {/* HERO */}
      <section className="section mx-auto max-w-6xl px-5">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow">AI Concierge</p>
            <h1 className="mt-3 font-serif text-5xl font-semibold leading-[1.05] sm:text-6xl">
              Your AI Concierge.
              <br />
              <span className="italic text-muted">Here to help, 24/7.</span>
            </h1>
            <p className="mt-5 max-w-md text-ink/70">
              Ask anything about your stay, our resort, San Vicente, or Palawan.
              Get instant answers and assistance.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-4">
              <a
                href="#chat"
                className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-warmwhite transition hover:opacity-90"
              >
                Start a conversation →
              </a>
              <span className="flex items-center gap-2 text-xs text-muted">
                <span className="text-forest">✓</span> Trained on our resort
                knowledge base
              </span>
            </div>
            <div className="mt-8 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
              {["Instant Answers", "Local Expertise", "Personalized Help", "Available 24/7"].map(
                (f) => (
                  <div key={f} className="rounded-xl bg-surface/50 px-3 py-3 text-center text-ink/80">
                    {f}
                  </div>
                ),
              )}
            </div>
          </div>

          <div id="chat">
            <ConciergeChat
              suggested={SUGGESTED_QUESTIONS}
              popularTopics={POPULAR_TOPICS}
            />
          </div>
        </div>
      </section>

      {/* MEET */}
      <section className="section bg-surface/40">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 lg:grid-cols-2">
          <div className="rounded-2xl bg-basalt p-8 text-warmwhite">
            <p className="eyebrow text-warmwhite/70">Powered by advanced AI</p>
            <h2 className="mt-3 font-serif text-3xl">Meet Your AI Concierge</h2>
            <p className="mt-3 text-warmwhite/80">
              Your concierge knows {profile.name} inside out — rooms, dining,
              tours, transport, and policies — and routes anything sensitive to
              our human team.
            </p>
            <a
              href="#chat"
              className="mt-5 inline-block rounded-full border border-warmwhite/50 px-5 py-2 text-sm font-semibold text-warmwhite transition hover:bg-warmwhite/10"
            >
              How it works
            </a>
          </div>
          <div className="grid gap-3 self-center">
            {[
              { t: "Knowledge Base", d: "Answers drawn from your resort's curated info." },
              { t: "Real-time Updates", d: "Availability and status, kept current." },
              { t: "Secure & Private", d: "Guest data stays with your resort." },
            ].map((c) => (
              <div key={c.t} className="card p-5">
                <p className="font-serif text-xl text-ink">{c.t}</p>
                <p className="mt-1 text-sm text-ink/70">{c.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOR GUESTS / TEAM */}
      <section className="section mx-auto max-w-6xl px-5">
        <h2 className="font-serif text-3xl">For Our Guests</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {GUEST_FEATURES.map((f) => (
            <div key={f.title} className="card p-6">
              <p className="font-serif text-xl text-ink">{f.title}</p>
              <p className="mt-2 text-sm text-ink/70">{f.desc}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-widest text-accent">
                {f.cta} →
              </p>
            </div>
          ))}
        </div>

        <h2 className="mt-12 font-serif text-3xl">For Our Team</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TEAM_FEATURES.map((f) => (
            <Link
              key={f.title}
              href="/admin"
              className="card p-6 no-underline transition hover:bg-surface/60"
            >
              <p className="font-serif text-xl text-ink">{f.title}</p>
              <p className="mt-2 text-sm text-ink/70">{f.desc}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-widest text-accent">
                {f.cta} →
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* FOOTER STATS */}
      <section className="border-t border-line bg-basalt text-warmwhite">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-serif text-xl">Can&apos;t find what you need?</p>
            <Link
              href="/admin"
              className="mt-2 inline-block rounded-full bg-warmwhite px-5 py-2 text-sm font-semibold text-ink transition hover:bg-sandstone"
            >
              Contact human team
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
