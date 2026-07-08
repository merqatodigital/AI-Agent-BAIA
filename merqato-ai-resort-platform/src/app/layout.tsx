import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Wordmark } from "@/components/brand/Logo";

export const metadata: Metadata = {
  title: "MerQato · AI Resort Website",
  description:
    "A complete, AI-powered website platform for small resorts, boutique hotels, villas and homestays. Concierge, admin, Mission Control and staff ops — built in.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-bg text-ink">
        <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
            <Link href="/" className="no-underline">
              <Wordmark size={34} />
            </Link>
            <nav className="flex items-center gap-6 text-sm font-medium text-ink/80">
              <a className="hidden sm:inline hover:text-accent" href="#rooms">
                Rooms
              </a>
              <a className="hidden sm:inline hover:text-accent" href="#experiences">
                Experiences
              </a>
              <a className="hidden sm:inline hover:text-accent" href="/concierge">
                AI Concierge
              </a>
              <a
                className="rounded-full border border-line px-4 py-2 text-ink transition hover:bg-surface"
                href="/admin"
              >
                Owner Login
              </a>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-line/70 bg-surface/40">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-8 text-sm text-ink/70 sm:flex-row sm:items-center sm:justify-between">
            <Wordmark size={26} showTagline={false} />
            <p>
              © {new Date().getFullYear()} MerQato · AI Resort Website. Powered
              by your own OpenRouter key.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
