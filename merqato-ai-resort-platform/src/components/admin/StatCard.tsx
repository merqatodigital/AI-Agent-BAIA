"use client";

export function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="card p-5">
      <p className="text-3xl font-semibold text-ink">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-widest text-muted">
        {label}
      </p>
    </div>
  );
}
