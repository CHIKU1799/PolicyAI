"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import MarketingShell from "@/components/marketing/Shell";
import { workerFetch } from "@/lib/supabase";

const PHONE = "+91-7004732371";

const SEGMENTS = [
  ["nbfc", "NBFC"],
  ["mfi", "Microfinance"],
  ["aif", "AIF / PMS"],
  ["payments", "Payment Aggregator / Gateway"],
  ["insurer", "Insurer"],
  ["other", "Other"],
];

const inputCls =
  "w-full rounded-xl border bg-white px-3.5 py-2.5 text-[14px] outline-none focus:border-[#1E5EF6]";
const inputStyle = { borderColor: "#E2E1DC", color: "#1A1C22" };

function ContactForm() {
  const params = useSearchParams();
  const intent = params.get("intent") === "sales" ? "sales" : "demo";
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    segment: "",
    phone: "",
    message: "",
    website: "", // honeypot
  });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const resp = await workerFetch("/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, intent, segment: form.segment || null }),
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => null);
        throw new Error(d?.detail?.[0]?.msg ?? `request failed (${resp.status})`);
      }
      setDone(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div
        className="mx-auto max-w-lg rounded-3xl border bg-white p-10 text-center"
        style={{ borderColor: "#EAE9E5", boxShadow: "0 16px 44px -16px rgba(21,37,78,.18)" }}
      >
        <div
          className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full text-[26px] text-white"
          style={{ background: "#1F9D5B" }}
        >
          ✓
        </div>
        <h2
          className="text-[28px] font-medium leading-snug"
          style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
        >
          Thank you, {form.name.split(" ")[0] || "there"}!
        </h2>
        <p className="mx-auto mt-2 max-w-sm text-[14px] leading-relaxed" style={{ color: "#54565E" }}>
          Your {intent === "demo" ? "demo request" : "message for our sales team"} is in. Our team
          will reach out to you soon on the details you shared.
        </p>
        <div
          className="mx-auto mt-6 inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-[14px] font-semibold"
          style={{ borderColor: "#E2E1DC", color: "#15254E" }}
        >
          <span aria-hidden>📞</span> Can&apos;t wait? Call us: {PHONE}
        </div>
        <p className="mt-4 text-[12px]" style={{ color: "#9A9DA4" }}>
          Mon-Sat, 10:00-19:00 IST
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="mx-auto max-w-lg rounded-3xl border bg-white p-8"
      style={{ borderColor: "#EAE9E5", boxShadow: "0 16px 44px -16px rgba(21,37,78,.18)" }}
    >
      <div className="grid gap-3.5">
        <input required minLength={2} placeholder="Your name" value={form.name} onChange={set("name")} className={inputCls} style={inputStyle} />
        <input required type="email" placeholder="Work email" value={form.email} onChange={set("email")} className={inputCls} style={inputStyle} />
        <input required minLength={2} placeholder="Company name" value={form.company} onChange={set("company")} className={inputCls} style={inputStyle} />
        <div className="grid grid-cols-2 gap-3.5">
          <select value={form.segment} onChange={set("segment")} className={inputCls} style={{ ...inputStyle, color: form.segment ? "#1A1C22" : "#9A9DA4" }}>
            <option value="">Segment (optional)</option>
            {SEGMENTS.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
          <input placeholder="Phone (optional)" value={form.phone} onChange={set("phone")} className={inputCls} style={inputStyle} />
        </div>
        <textarea
          rows={4}
          placeholder={intent === "demo" ? "What would you like to see in the demo?" : "How can our sales team help?"}
          value={form.message}
          onChange={set("message")}
          className={inputCls}
          style={inputStyle}
        />
        {/* honeypot, hidden from humans */}
        <input tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} className="hidden" aria-hidden />
      </div>
      {error && (
        <p className="mt-3 text-[12.5px]" style={{ color: "#C0392B" }}>
          Couldn&apos;t submit: {error}
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="mt-5 w-full rounded-xl py-3 text-[14.5px] font-semibold text-white disabled:opacity-60"
        style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)", boxShadow: "0 2px 10px rgba(23,70,214,.35)" }}
      >
        {busy ? "Sending…" : intent === "demo" ? "Request my demo" : "Contact sales"}
      </button>
      <p className="mt-3 text-center text-[12px]" style={{ color: "#9A9DA4" }}>
        Prefer to talk now? Call {PHONE} (Mon-Sat, 10:00-19:00 IST)
      </p>
    </form>
  );
}

function ContactHeader() {
  const params = useSearchParams();
  const intent = params.get("intent") === "sales" ? "sales" : "demo";
  return (
    <div className="mx-auto max-w-2xl pb-8 text-center">
      <div
        className="mx-auto mb-4 inline-block rounded-full border bg-white px-3 py-1 text-[11px] font-semibold tracking-wide"
        style={{ borderColor: "#E2E1DC", color: "#1746D6" }}
      >
        {intent === "demo" ? "BOOK A DEMO" : "TALK TO SALES"}
      </div>
      <h1
        className="text-[42px] font-medium leading-[1.1] tracking-tight md:text-[50px]"
        style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
      >
        {intent === "demo" ? (
          <>
            See PolicyAI on your
            <br />
            segment&apos;s regulations
          </>
        ) : (
          <>
            Let&apos;s talk about
            <br />
            your compliance stack
          </>
        )}
      </h1>
      <p className="mx-auto mt-3 max-w-md text-[14.5px] leading-relaxed" style={{ color: "#54565E" }}>
        {intent === "demo"
          ? "Thirty minutes, live on the real platform: your entity class, your regulators, your gaps."
          : "Pricing, procurement, security questionnaires, or a bespoke rollout: tell us what you need."}
      </p>
    </div>
  );
}

export default function ContactPage() {
  return (
    <MarketingShell>
      <div className="px-5 pb-20 pt-14">
        <Suspense fallback={null}>
          <ContactHeader />
          <ContactForm />
        </Suspense>
      </div>
    </MarketingShell>
  );
}
