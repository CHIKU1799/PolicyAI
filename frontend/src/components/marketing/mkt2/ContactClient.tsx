"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { workerFetch } from "@/lib/supabase";
import {
  ACCENT,
  BODY,
  FAINT,
  GREEN,
  INK,
  Kicker,
  LINE,
  MUTED,
} from "@/components/marketing/mkt2/ui";

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
  "w-full rounded-xl border bg-white px-3.5 py-2.5 text-[14px] outline-none focus:border-[#4B40C4]";
const inputStyle = { borderColor: "#E2E1DC", color: "#1A1C22" };

function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor: string }) {
  return (
    <label
      htmlFor={htmlFor}
      className="mono mb-1.5 block text-[10px] font-semibold tracking-[.14em]"
      style={{ color: MUTED }}
    >
      {children}
    </label>
  );
}

function ContactInner() {
  const params = useSearchParams();
  const initialIntent = params.get("intent") === "sales" ? "sales" : "demo";
  const [form, setForm] = useState({
    intent: initialIntent,
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

  const set =
    (k: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  const intent = form.intent === "sales" ? "sales" : "demo";

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

  const card = done ? (
    <div
      className="anim-rise rounded-[20px] border bg-white p-8 text-center md:p-10"
      style={{ borderColor: LINE, boxShadow: "0 18px 44px -18px rgba(17,18,27,.22)" }}
    >
      <div
        className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full text-[26px] text-white"
        style={{ background: GREEN }}
      >
        ✓
      </div>
      <h2 className="serif m-0 text-[28px] font-medium leading-snug tracking-[-0.02em]" style={{ color: INK }}>
        Thank you, {form.name.split(" ")[0] || "there"}!
      </h2>
      <p className="mx-auto mb-0 mt-2.5 max-w-sm text-[14px] leading-relaxed" style={{ color: BODY }}>
        Your {intent === "demo" ? "demo request" : "message for our sales team"} is in. We will reach
        out within one business day on the details you shared.
      </p>
      <div
        className="mx-auto mt-6 inline-flex items-center gap-2 rounded-[12px] border px-4 py-2.5 text-[14px] font-semibold"
        style={{ borderColor: "#E2E1DC", color: INK }}
      >
        <span aria-hidden>📞</span> Can&apos;t wait? Call us: {PHONE}
      </div>
      <p className="mb-0 mt-4 text-[12px]" style={{ color: FAINT }}>
        Mon-Sat, 10:00-19:00 IST
      </p>
    </div>
  ) : (
    <form
      onSubmit={submit}
      className="anim-rise rounded-[20px] border bg-white p-6 md:p-8"
      style={{ borderColor: LINE, boxShadow: "0 18px 44px -18px rgba(17,18,27,.22)" }}
    >
      <div className="grid gap-4">
        <div>
          <Label htmlFor="ct-intent">I WANT TO</Label>
          <select id="ct-intent" value={form.intent} onChange={set("intent")} className={inputCls} style={inputStyle}>
            <option value="demo">Book a demo</option>
            <option value="sales">Talk to sales</option>
          </select>
        </div>
        <div>
          <Label htmlFor="ct-name">YOUR NAME</Label>
          <input id="ct-name" required minLength={2} placeholder="Your name" value={form.name} onChange={set("name")} className={inputCls} style={inputStyle} />
        </div>
        <div>
          <Label htmlFor="ct-email">WORK EMAIL</Label>
          <input id="ct-email" required type="email" placeholder="you@company.in" value={form.email} onChange={set("email")} className={inputCls} style={inputStyle} />
        </div>
        <div>
          <Label htmlFor="ct-company">COMPANY</Label>
          <input id="ct-company" required minLength={2} placeholder="Company name" value={form.company} onChange={set("company")} className={inputCls} style={inputStyle} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="ct-segment">SEGMENT (OPTIONAL)</Label>
            <select
              id="ct-segment"
              value={form.segment}
              onChange={set("segment")}
              className={inputCls}
              style={{ ...inputStyle, color: form.segment ? "#1A1C22" : "#9A9DA4" }}
            >
              <option value="">Select a segment</option>
              {SEGMENTS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="ct-phone">PHONE (OPTIONAL)</Label>
            <input id="ct-phone" placeholder="+91" value={form.phone} onChange={set("phone")} className={inputCls} style={inputStyle} />
          </div>
        </div>
        <div>
          <Label htmlFor="ct-message">MESSAGE</Label>
          <textarea
            id="ct-message"
            rows={4}
            placeholder={
              intent === "demo"
                ? "What would you like to see in the demo?"
                : "How can our sales team help?"
            }
            value={form.message}
            onChange={set("message")}
            className={inputCls}
            style={inputStyle}
          />
        </div>
        {/* honeypot, hidden from humans */}
        <input tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} className="hidden" aria-hidden />
      </div>
      {error && (
        <p
          className="mt-4 rounded-[10px] border px-3.5 py-2.5 text-[12.5px]"
          style={{ borderColor: "#F3D2CC", background: "#FDECEC", color: "#C0392B" }}
        >
          Couldn&apos;t submit: {error}. You can also call us on {PHONE}.
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="mt-5 w-full rounded-[14px] py-3.5 text-[15px] font-semibold text-white disabled:opacity-60"
        style={{ background: ACCENT, boxShadow: "0 8px 22px rgba(75,64,196,.26)" }}
      >
        {busy ? "Sending…" : intent === "demo" ? "Request my demo" : "Contact sales"}
      </button>
      <p className="mb-0 mt-3 text-center text-[12px]" style={{ color: FAINT }}>
        Prefer to talk now? Call {PHONE} (Mon-Sat, 10:00-19:00 IST)
      </p>
    </form>
  );

  return (
    <div className="grid items-start gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-14">
      {/* Left: pitch and expectations */}
      <div className="flex flex-col gap-7 lg:sticky lg:top-24">
        <div className="anim-rise flex flex-col gap-5">
          <Kicker>{intent === "demo" ? "BOOK A DEMO" : "TALK TO SALES"}</Kicker>
          <h1 className="serif m-0 max-w-[16ch] text-balance text-[36px] font-medium leading-[1.07] tracking-[-0.02em] sm:text-[44px] md:text-[52px]">
            {intent === "demo"
              ? "See PolicyAI on your segment's regulations"
              : "Let's talk about your compliance stack"}
          </h1>
          <p className="m-0 max-w-[52ch] text-pretty text-[15.5px] leading-relaxed md:text-[16.5px]" style={{ color: BODY }}>
            {intent === "demo"
              ? "Thirty minutes, live on the real platform: your entity class, your regulators, your gaps. No slideware."
              : "Pricing, procurement, security questionnaires, or a bespoke rollout: tell us what you need and we will come prepared."}
          </p>
        </div>

        <ul className="m-0 flex list-none flex-col gap-3.5 p-0">
          {[
            ["We reply within one business day", "A human reads every message; there is no ticket queue."],
            [
              "The demo runs on the live platform",
              "Your entity class, the regulators that bind you, and a real gap analysis, not a recorded deck.",
            ],
            [
              "Security answers on request",
              "Vendor-risk questionnaires answered within one business week; architecture walkthroughs for your security team.",
            ],
          ].map(([t, s]) => (
            <li key={t} className="flex items-start gap-3">
              <span
                aria-hidden
                className="mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full text-[12px] font-bold"
                style={{ background: "rgba(75,64,196,.1)", color: ACCENT }}
              >
                ✓
              </span>
              <span>
                <span className="block text-[14.5px] font-bold" style={{ color: INK }}>
                  {t}
                </span>
                <span className="block text-[13px] leading-relaxed" style={{ color: MUTED }}>
                  {s}
                </span>
              </span>
            </li>
          ))}
        </ul>

        <div
          className="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-[16px] border bg-white px-5 py-4 text-[13px]"
          style={{ borderColor: LINE, color: "#3A3D44" }}
        >
          <span className="flex items-center gap-2 font-semibold">
            <span aria-hidden>📞</span> {PHONE}
          </span>
          <span style={{ color: FAINT }}>Mon-Sat, 10:00-19:00 IST</span>
        </div>
      </div>

      {/* Right: the form */}
      <div>{card}</div>
    </div>
  );
}

export default function ContactClient() {
  return (
    <Suspense fallback={null}>
      <ContactInner />
    </Suspense>
  );
}
