import { getDataStore, DEFAULT_RESORT_ID } from "@/lib/data";
import { ConciergeWidget } from "@/components/guest/ConciergeWidget";
import { InquiryForm } from "@/components/guest/InquiryForm";

export default async function HomePage() {
  const store = getDataStore();
  const profile = await store.getResortProfile(DEFAULT_RESORT_ID);

  return (
    <div>
      {/* HERO */}
      <section className="relative">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${profile.heroImageUrl})` }}
          aria-hidden
        />
        <div className="absolute inset-0 bg-gradient-to-b from-basalt/55 via-basalt/35 to-basalt/70" />
        <div className="relative mx-auto flex min-h-[88vh] max-w-6xl flex-col justify-center px-5 text-warmwhite">
          <p className="eyebrow text-warmwhite/80">{profile.location}</p>
          <h1 className="mt-4 max-w-3xl font-serif text-5xl font-semibold leading-[1.05] sm:text-7xl">
            {profile.name}
          </h1>
          <p className="mt-5 max-w-xl text-lg text-warmwhite/90">
            {profile.tagline} {profile.description}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="#rooms"
              className="rounded-full bg-warmwhite px-6 py-3 text-sm font-semibold text-ink transition hover:bg-sandstone"
            >
              View Rooms
            </a>
            <a
              href="#concierge"
              className="rounded-full border border-warmwhite/60 px-6 py-3 text-sm font-semibold text-warmwhite transition hover:bg-warmwhite/10"
            >
              Talk to the AI Concierge
            </a>
          </div>
        </div>
      </section>

      {/* AMENITIES */}
      <section className="section mx-auto max-w-6xl px-5">
        <p className="eyebrow">The Experience</p>
        <h2 className="mt-3 font-serif text-4xl">Everything you need, nothing you don&apos;t</h2>
        <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3">
          {profile.amenities.map((a) => (
            <div
              key={a}
              className="card flex items-center justify-center px-4 py-8 text-center font-medium text-ink"
            >
              {a}
            </div>
          ))}
        </div>
      </section>

      {/* ROOMS */}
      <section id="rooms" className="section mx-auto max-w-6xl px-5">
        <p className="eyebrow">Stay</p>
        <h2 className="mt-3 font-serif text-4xl">Rooms & Villas</h2>
        <div className="mt-8 grid gap-6 sm:grid-cols-2">
          {profile.rooms.map((r) => (
            <article key={r.id} className="card overflow-hidden">
              <div
                className="h-56 bg-cover bg-center"
                style={{ backgroundImage: `url(${r.imageUrl})` }}
                aria-hidden
              />
              <div className="p-6">
                <div className="flex items-baseline justify-between gap-4">
                  <h3 className="font-serif text-2xl">{r.name}</h3>
                  <p className="text-muted">
                    ${r.pricePerNight}
                    <span className="text-ink/50"> / night</span>
                  </p>
                </div>
                <p className="mt-2 text-sm text-ink/70">{r.description}</p>
                <p className="mt-3 text-xs uppercase tracking-widest text-muted">
                  Sleeps {r.capacity}
                </p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* EXPERIENCES */}
      <section id="experiences" className="section bg-surface/40">
        <div className="mx-auto max-w-6xl px-5">
          <p className="eyebrow">Discover</p>
          <h2 className="mt-3 font-serif text-4xl">Experiences</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {profile.tours.map((t) => (
              <div key={t.id} className="card p-6">
                <h3 className="font-serif text-xl">{t.name}</h3>
                <p className="mt-2 text-sm text-ink/70">{t.description}</p>
                <p className="mt-3 text-sm text-muted">
                  {t.duration} · ${t.price}
                </p>
              </div>
            ))}
            {profile.restaurants.map((r) => (
              <div key={r.id} className="card p-6">
                <h3 className="font-serif text-xl">{r.name}</h3>
                <p className="mt-2 text-sm text-ink/70">{r.cuisine}</p>
                <p className="mt-3 text-sm text-muted">{r.hours}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CONCIERGE + INQUIRY */}
      <section id="concierge" className="section mx-auto max-w-6xl px-5">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow">Always on</p>
            <h2 className="mt-3 font-serif text-4xl">
              A concierge that never sleeps
            </h2>
            <p className="mt-4 max-w-md text-ink/70">
              Guests get instant, accurate answers from your resort&apos;s knowledge
              base — rooms, tours, dining, transport and policies. Sensitive
              requests are routed to your team for approval.
            </p>
            <div className="mt-8">
              <InquiryForm />
            </div>
          </div>
          <div className="flex justify-center">
            <ConciergeWidget />
          </div>
        </div>
      </section>

      {/* POLICIES */}
      <section className="section bg-surface/40">
        <div className="mx-auto max-w-3xl px-5 text-center">
          <p className="eyebrow">Good to know</p>
          <p className="mt-4 font-serif text-2xl leading-relaxed text-ink/80">
            {profile.policies}
          </p>
        </div>
      </section>
    </div>
  );
}
