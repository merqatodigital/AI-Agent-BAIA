"use client";

import { useState } from "react";

/**
 * Booking inquiry form. Submits to /api/inquiry and creates a real inquiry
 * record (pending human follow-up). Never confirms a booking autonomously.
 */
export function InquiryForm() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    message: "",
    checkIn: "",
    checkOut: "",
    guests: "2",
  });
  const [status, setStatus] = useState<"idle" | "sending" | "done" | "error">(
    "idle",
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    try {
      const res = await fetch("/api/inquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error();
      setStatus("done");
      setForm({ name: "", email: "", message: "", checkIn: "", checkOut: "", guests: "2" });
    } catch {
      setStatus("error");
    }
  }

  if (status === "done") {
    return (
      <div className="card p-6 text-center">
        <p className="font-serif text-2xl text-accent">Thank you</p>
        <p className="mt-2 text-sm text-ink/70">
          We&apos;ve received your request and a team member will be in touch to
          confirm availability.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="card space-y-3 p-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          required
          placeholder="Your name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
        />
        <input
          required
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
        />
        <input
          type="date"
          value={form.checkIn}
          onChange={(e) => setForm({ ...form, checkIn: e.target.value })}
          className="rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
        />
        <input
          type="date"
          value={form.checkOut}
          onChange={(e) => setForm({ ...form, checkOut: e.target.value })}
          className="rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
        />
      </div>
      <input
        type="number"
        min={1}
        value={form.guests}
        onChange={(e) => setForm({ ...form, guests: e.target.value })}
        placeholder="Guests"
        className="w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
      />
      <textarea
        required
        rows={3}
        placeholder="What are you looking for?"
        value={form.message}
        onChange={(e) => setForm({ ...form, message: e.target.value })}
        className="w-full rounded-xl border border-line bg-bg px-4 py-2 text-sm outline-none focus:border-accent"
      />
      <button
        type="submit"
        disabled={status === "sending"}
        className="w-full rounded-full bg-accent px-6 py-3 text-sm font-semibold text-warmwhite transition hover:opacity-90 disabled:opacity-50"
      >
        {status === "sending" ? "Sending…" : "Request to Book"}
      </button>
      {status === "error" && (
        <p className="text-center text-sm text-danger">
          Something went wrong. Please try again.
        </p>
      )}
    </form>
  );
}
