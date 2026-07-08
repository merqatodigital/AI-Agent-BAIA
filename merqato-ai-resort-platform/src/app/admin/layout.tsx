import Link from "next/link";
import { Wordmark } from "@/components/brand/Logo";

const NAV = [
  { href: "/admin", label: "Mission Control" },
  { href: "/admin/resort", label: "Resort Editor" },
  { href: "/admin/knowledge", label: "Knowledge Base" },
  { href: "/admin/approvals", label: "Approvals" },
  { href: "/admin/openrouter", label: "OpenRouter" },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-bg">
      <div className="mx-auto flex max-w-7xl flex-col sm:flex-row">
        <aside className="border-b border-line bg-surface/40 p-5 sm:w-64 sm:border-b-0 sm:border-r">
          <Link href="/" className="no-underline">
            <Wordmark size={30} />
          </Link>
          <p className="mt-1 text-xs uppercase tracking-widest text-muted">
            Owner Workspace
          </p>
          <nav className="mt-6 flex flex-col gap-1">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className="rounded-xl px-3 py-2 text-sm font-medium text-ink/80 no-underline transition hover:bg-warmwhite"
              >
                {n.label}
              </Link>
            ))}
          </nav>
        </aside>
        <section className="flex-1 p-6 sm:p-10">{children}</section>
      </div>
    </div>
  );
}
