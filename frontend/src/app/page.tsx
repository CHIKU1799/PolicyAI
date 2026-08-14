import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import DashboardMock, { sparkPath } from "@/components/marketing/DashboardMock";
import LiveIntelBand from "@/components/marketing/LiveIntelBand";
import { AmbientDepth, Reveal } from "@/components/marketing/PaiMotion";

// Public marketing landing page. The product lives behind /login -> /dashboard.

const MODULES = [
  {
    step: "01 · MONITOR",
    title: "Horizon scanning",
    body: "RBI, SEBI, IRDAI and MeitY watched continuously, with deep archive backfill and severity scoring against your business.",
    bullets: ["Real-time AI alerts", "Multi-regulator coverage"],
  },
  {
    step: "02 · STRUCTURE",
    title: "Obligation extraction",
    body: "Each update becomes discrete obligations, mapped to policy, owner, control and product with full traceability.",
    bullets: ["AI extraction, any document", "Rule-to-action lineage"],
  },
  {
    step: "03 · ASSESS",
    title: "Gap analysis",
    body: "Coverage classified per requirement, triaged by severity, with the exact policy passage as citable evidence.",
    bullets: ["Coverage per requirement", "AI remediation steps"],
  },
  {
    step: "04 · TEST",
    title: "Controls testing",
    body: "Continuous effectiveness testing with 12-week trends, so drift surfaces the moment it starts.",
    bullets: ["Pass-rate history", "Alerts on failure"],
  },
  {
    step: "05 · GOVERN",
    title: "Policy governance",
    body: "Central library with versioning, review and approval workflows, and an exportable audit trail.",
    bullets: ["Version control", "Exportable audit trail"],
  },
];

const CONTROL_ROWS = [
  { name: "Forbearance eligibility check", value: "96%", color: "#1F9D5B", chipBg: "#E8F6EE", path: sparkPath(7, true) },
  { name: "Late-fee suppression", value: "99%", color: "#1F9D5B", chipBg: "#E8F6EE", path: sparkPath(8, true) },
  { name: "Fairness monitor: credit model", value: "58%", color: "#C0392B", chipBg: "#FDECEC", path: sparkPath(9, false) },
  { name: "Vendor due-diligence refresh", value: "74%", color: "#E0683C", chipBg: "#FFF3E6", path: sparkPath(10, false) },
];

const CITATIONS = ["RBI/2025-26/14 ¶12", "POL-04 §2.1", "OBL-1044"];

export default function Home() {
  return (
    <MarketingShell>
      <main className="relative mx-auto flex max-w-[1304px] flex-col gap-20 px-5 pb-24 pt-12 md:gap-[104px] md:px-8 md:pt-16">
        <AmbientDepth />
        {/* Hero */}
        <section className="anim-rise relative z-10 flex flex-col items-center gap-6 text-center md:gap-[26px]">
          <span className="mono text-[11px] font-semibold tracking-[.18em]" style={{ color: "#71757E" }}>
            REGULATORY INTELLIGENCE FOR INDIAN BFSI
          </span>
          <h1 className="serif m-0 max-w-[16ch] text-balance text-[40px] font-medium leading-[1.06] tracking-[-0.02em] sm:text-[54px] md:text-[66px] md:leading-[1.04]">
            Every circular, mapped to the obligation it creates.
          </h1>
          <p className="m-0 max-w-[60ch] text-pretty text-[16px] leading-relaxed md:text-[18px]" style={{ color: "#5B5E66" }}>
            PolicyAI watches RBI, SEBI, IRDAI and MeitY around the clock, turns each update into
            clear obligations for your firm, and tracks them through controls, evidence and
            approvals, so nothing slips through.
          </p>
          <div className="mt-1.5 flex flex-wrap justify-center gap-3.5">
            <Link
              href="/login"
              className="inline-flex items-center gap-2.5 rounded-[14px] px-[26px] py-4 text-[16px] font-semibold text-white no-underline"
              style={{ background: "#4B40C4", boxShadow: "0 8px 22px rgba(75,64,196,.26)" }}
            >
              Explore the platform <span aria-hidden className="text-[18px]">→</span>
            </Link>
            <a
              href="#live"
              className="inline-flex items-center gap-2.5 rounded-[14px] border bg-white px-[26px] py-4 text-[16px] font-semibold no-underline"
              style={{ borderColor: "#EAE9E5", color: "#15161B" }}
            >
              See it live
            </a>
          </div>
          <div className="text-[13.5px]" style={{ color: "#9A9DA4" }}>
            Secure by design · Org-isolated data · No card required for trial
          </div>
        </section>

        {/* Product mock */}
        <Reveal className="relative z-10">
          <DashboardMock />
        </Reveal>

        {/* Live intel band: real corpus numbers and the latest circulars */}
        <section id="live" className="relative z-10 flex scroll-mt-24 flex-col gap-[22px]">
          <div className="flex flex-wrap items-end gap-7">
            <div className="min-w-[280px] flex-1 sm:min-w-[340px]">
              <span className="mono text-[11px] font-semibold tracking-[.18em]" style={{ color: "#71757E" }}>
                LIVE REGULATORY INTELLIGENCE
              </span>
              <h2 className="serif mb-0 mt-2.5 text-[32px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[42px]">
                Watching the regulators. Right now.
              </h2>
            </div>
            <p
              className="m-0 min-w-[280px] flex-1 text-pretty text-[15.5px] leading-[1.65] sm:min-w-[320px]"
              style={{ color: "#5B5E66" }}
            >
              This is the platform&apos;s own corpus, live on the page: what the crawler has ingested,
              which regulator published what, and the newest circulars, minutes after they land on
              the regulator&apos;s site.
            </p>
          </div>
          <Reveal>
            <LiveIntelBand />
          </Reveal>
        </section>

        {/* Modules */}
        <section id="modules" className="relative z-10 flex flex-col gap-[26px]">
          <div className="flex flex-wrap items-end gap-7">
            <h2 className="serif m-0 min-w-[280px] flex-1 text-[32px] font-medium leading-[1.1] tracking-[-0.02em] sm:min-w-[320px] md:text-[42px]">
              One connected system, end to end
            </h2>
            <p className="m-0 min-w-[280px] flex-1 text-[15.5px] leading-[1.65] sm:min-w-[320px]" style={{ color: "#5B5E66" }}>
              Five modules on the same graph. A signal picked up on Monday is a tested control with
              citable evidence by Friday.
            </p>
          </div>
          <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-5">
            {MODULES.map((m, i) => (
              <Link
                key={m.title}
                href="/platform"
                className="anim-rise flex min-h-[230px] flex-col gap-2.5 rounded-[18px] border bg-white p-5 pr-[18px] text-left no-underline transition-[box-shadow,transform] duration-300 hover:-translate-y-[3px] hover:shadow-[0_14px_30px_-14px_rgba(17,18,27,.25)]"
                style={{ borderColor: "#EAE9E5", animationDelay: `${i * 0.07}s` }}
              >
                <span className="mono text-[10.5px] font-semibold tracking-[.12em]" style={{ color: "#4B40C4" }}>
                  {m.step}
                </span>
                <div className="text-[17px] font-bold leading-tight tracking-[-0.01em]" style={{ color: "#15161B" }}>
                  {m.title}
                </div>
                <div className="text-pretty text-[13px] leading-relaxed" style={{ color: "#71757E" }}>
                  {m.body}
                </div>
                <div className="mt-auto flex flex-col gap-[5px]">
                  {m.bullets.map((b) => (
                    <div key={b} className="flex gap-[7px] text-[12px]" style={{ color: "#3A3D44" }}>
                      <span style={{ color: "#1F9D5B" }}>✓</span>
                      {b}
                    </div>
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Ask PolicyAI + Controls & Tasks */}
        <section className="relative z-10 grid gap-5 lg:grid-cols-2">
          <div className="flex flex-col gap-4 rounded-[20px] border bg-white p-6 md:p-[26px]" style={{ borderColor: "#EAE9E5" }}>
            <div>
              <span className="mono text-[10.5px] font-semibold tracking-[.16em]" style={{ color: "#71757E" }}>
                ASK POLICYAI
              </span>
              <h3 className="mb-0 mt-[9px] text-[22px] font-bold tracking-[-0.02em] md:text-[24px]">
                Answers with the paragraph attached
              </h3>
            </div>
            <div
              className="flex flex-col gap-[11px] rounded-[14px] border p-3.5"
              style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}
            >
              <div className="text-[13px] font-semibold" style={{ color: "#15161B" }}>
                “Which of our policies fail the new digital lending disclosure rules?”
              </div>
              <div className="text-[12.5px] leading-relaxed" style={{ color: "#3A3D44" }}>
                Three policies fall short of the key-fact-statement requirement. POL-04 §2.1
                references the older cooling-off text and has no pre-disbursal disclosure clause.
              </div>
              <div className="flex flex-wrap gap-1.5">
                {CITATIONS.map((c) => (
                  <span
                    key={c}
                    className="mono rounded-md border px-[7px] py-[3px] text-[10px]"
                    style={{ borderColor: "#EAE9E5", color: "#4B40C4" }}
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
            <div className="text-[12.5px] leading-relaxed" style={{ color: "#71757E" }}>
              Retrieval runs over your policy library and the regulator corpus together: every claim
              is traceable back to the source paragraph.
            </div>
          </div>
          <div className="flex flex-col gap-4 rounded-[20px] border bg-white p-6 md:p-[26px]" style={{ borderColor: "#EAE9E5" }}>
            <div>
              <span className="mono text-[10.5px] font-semibold tracking-[.16em]" style={{ color: "#71757E" }}>
                CONTROLS &amp; TASKS
              </span>
              <h3 className="mb-0 mt-[9px] text-[22px] font-bold tracking-[-0.02em] md:text-[24px]">
                Drift shows up before the audit does
              </h3>
            </div>
            {CONTROL_ROWS.map((c) => (
              <div key={c.name} className="flex items-center gap-3 border-t pt-[11px]" style={{ borderColor: "#F4F4F1" }}>
                <span className="flex-1 text-[13px]" style={{ color: "#3A3D44" }}>
                  {c.name}
                </span>
                <svg viewBox="0 0 90 20" preserveAspectRatio="none" className="h-5 w-[70px] sm:w-[90px]" aria-hidden>
                  <path d={c.path} fill="none" stroke={c.color} strokeWidth="1.6" strokeLinecap="round" />
                </svg>
                <span
                  className="min-w-[52px] rounded-[7px] px-2 py-[3px] text-center text-[11px] font-bold"
                  style={{ background: c.chipBg, color: c.color }}
                >
                  {c.value}
                </span>
              </div>
            ))}
            <div className="mt-auto text-[12.5px] leading-relaxed" style={{ color: "#71757E" }}>
              Failing tests open owned tasks automatically, with the obligation, control and
              evidence already attached.
            </div>
          </div>
        </section>

        {/* CTA band */}
        <Reveal className="relative z-10">
        <section
          className="flex flex-wrap items-center gap-10 rounded-3xl p-8 sm:p-12 md:p-14"
          style={{ background: "#15161B", color: "#F5F4F2" }}
        >
          <div className="min-w-[280px] flex-1 sm:min-w-[330px]">
            <h2 className="serif m-0 text-[30px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[40px]">
              See your compliance posture in one place
            </h2>
            <p className="mb-0 mt-3.5 max-w-[52ch] text-[15px] leading-relaxed md:text-[16px]" style={{ color: "#A7ABB4" }}>
              Join the compliance teams who turn regulatory change into action, without the
              spreadsheets.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/login"
              className="rounded-[14px] px-[26px] py-4 text-[16px] font-semibold text-white no-underline"
              style={{ background: "#4B40C4" }}
            >
              Start free trial
            </Link>
            <Link
              href="/contact?intent=sales"
              className="rounded-[14px] border px-[26px] py-4 text-[16px] font-semibold no-underline"
              style={{ borderColor: "#34363F", color: "#F5F4F2" }}
            >
              Book a walkthrough
            </Link>
          </div>
        </section>
        </Reveal>
      </main>
    </MarketingShell>
  );
}
