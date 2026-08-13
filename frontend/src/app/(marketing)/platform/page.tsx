import type { Metadata } from "next";
import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import { sparkPath } from "@/components/marketing/DashboardMock";
import {
  CitationChip,
  CtaBand,
  PageHero,
  SplitSection,
  ToneChip,
  VignetteBar,
  VignetteCard,
  VignetteRow,
} from "@/components/marketing/PageSections";

export const metadata: Metadata = {
  title: "Platform · PolicyAI",
  description:
    "Five modules that turn regulatory change into action, end to end, on a shared knowledge graph.",
};

const FEED_ROWS = [
  { mono: "RBI", text: "Digital Lending Directions: disclosure obligations updated", chip: "High", tone: "red" as const },
  { mono: "SEBI", text: "Cybersecurity framework for regulated entities", chip: "Medium", tone: "amber" as const },
  { mono: "IRDAI", text: "Expenses-of-management circular refresh", chip: "Low", tone: "neutral" as const },
  { mono: "MeitY", text: "DPDP consent-manager rules notified", chip: "Medium", tone: "amber" as const },
];

const OBLIGATION_ROWS = [
  { mono: "OBL-1044", text: "Offer key-fact statement before disbursal", chip: "No owner", tone: "red" as const },
  { mono: "OBL-1045", text: "No fees on active repayment plans", chip: "In review", tone: "amber" as const },
  { mono: "OBL-1046", text: "Evidence borrower-consent rationale", chip: "Mapped", tone: "green" as const },
  { mono: "OBL-1047", text: "Report concentration risk to board", chip: "Mapped", tone: "green" as const },
];

const COVERAGE_BARS = [
  { label: "Audit trail for forbearance", pct: 28, color: "#C0392B" },
  { label: "Board concentration reporting", pct: 76, color: "#E0683C" },
  { label: "Fairness testing: credit", pct: 45, color: "#E0683C" },
  { label: "Enhanced CDD triggers", pct: 85, color: "#1F9D5B" },
];

const CONTROL_ROWS = [
  { mono: "CTL-014", text: "Forbearance eligibility", chip: "96%", tone: "green" as const, stroke: "#1F9D5B", path: sparkPath(7, true) },
  { mono: "CTL-021", text: "Late-fee suppression", chip: "99%", tone: "green" as const, stroke: "#1F9D5B", path: sparkPath(8, true) },
  { mono: "CTL-036", text: "Fairness monitor", chip: "58%", tone: "red" as const, stroke: "#C0392B", path: sparkPath(9, false) },
];

const VERSION_ROWS = [
  { mono: "v4.3", text: "Digital Lending disclosure obligations", chip: "CURRENT", tone: "green" as const },
  { mono: "v4.2", text: "Annual review, §2 clarifications" },
  { mono: "v4.1", text: "Added debt-advice signposting" },
];

const PIPELINE = [
  {
    step: "01 · CRAWL",
    title: "Every source, every 6 hours",
    body: "RBI, SEBI, IRDAI, CERT-In, FIU-IND and more, deduplicated by content hash so nothing is processed twice.",
  },
  {
    step: "02 · EXTRACT",
    title: "Circulars become a graph",
    body: "Obligations, entity classes, deadlines and amendment edges extracted into the live knowledge graph.",
  },
  {
    step: "03 · MAP",
    title: "Matched to your policies",
    body: "Your uploaded policy library is diffed against applicable requirements, coverage classified per requirement.",
  },
  {
    step: "04 · TRACK",
    title: "Owned to closure",
    body: "Gaps open tasks with owners and due dates; controls and approvals keep the trail audit-ready.",
  },
];

const CITATIONS = ["RBI/2025-26/14 ¶12", "POL-04 §2.1", "OBL-1044"];

export default function PlatformPage() {
  return (
    <MarketingShell>
      <main className="mx-auto flex max-w-[1304px] flex-col gap-16 px-5 pb-24 pt-12 md:gap-[88px] md:px-8 md:pt-16">
        <PageHero
          kicker="THE PLATFORM"
          title={
            <>
              One connected system,
              <br />
              end to end
            </>
          }
          lede="From the first regulatory signal to an audit-ready policy: five modules that work as one continuous workflow, on a shared knowledge graph."
        />

        <SplitSection
          id="monitor"
          kicker="01 · MONITOR"
          title="Horizon scanning"
          body="Continuously monitor RBI, SEBI, IRDAI and more, with deep archive backfill. Every update is summarised within hours and scored against your business, so your team reads a briefing, not a backlog."
          bullets={[
            "Real-time AI alerts with severity scoring",
            "Multi-regulator source coverage",
            "Filtered press feeds: regulatory actions only",
          ]}
        >
          <VignetteCard
            title="Live regulatory feed"
            badge="● LIVE"
            badgeTone="green"
            footer="Summarised within hours, severity-scored against your entity profile."
          >
            {FEED_ROWS.map((r) => (
              <VignetteRow key={r.text} {...r} />
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="structure"
          kicker="02 · STRUCTURE"
          title="Change becomes structured obligations"
          body="Each regulatory update becomes discrete, trackable obligations, automatically mapped to the right policies, owners, controls and products."
          bullets={[
            "AI extraction from any document",
            "Mapped to policy, owner, control, product",
            "Full traceability from rule to action",
          ]}
          flip
        >
          <VignetteCard
            title="RBI Digital Lending Directions"
            badge="4 OBLIGATIONS"
            badgeTone="indigo"
            footer="Every obligation keeps a pointer back to the exact circular paragraph."
          >
            {OBLIGATION_ROWS.map((r) => (
              <VignetteRow key={r.mono} {...r} />
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="assess"
          kicker="03 · ASSESS"
          title="Gap analysis"
          body="Compare your policies, processes and controls against emerging requirements. See coverage and severity at a glance, and close gaps before they become findings, with the exact policy passage as citable evidence."
          bullets={[
            "Coverage classification per requirement",
            "Severity-based triage",
            "AI-suggested remediation steps",
          ]}
        >
          <VignetteCard
            title="Coverage vs requirements"
            badge="12 GAPS"
            badgeTone="amber"
            footer="Four coverage states per requirement, from covered to absent."
          >
            {COVERAGE_BARS.map((b) => (
              <VignetteBar key={b.label} {...b} />
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="test"
          kicker="04 · TEST"
          title="Controls testing & monitoring"
          body="Real-time control effectiveness with continuous testing and trend monitoring. Know the moment a control starts to drift, not at the next audit."
          bullets={[
            "Test history with pass-rate trends",
            "12-week effectiveness chart",
            "Alerts the moment a control fails",
          ]}
          flip
        >
          <VignetteCard
            title="Control effectiveness"
            badge="● LIVE"
            badgeTone="green"
            footer="Failing tests open owned tasks automatically, evidence attached."
          >
            {CONTROL_ROWS.map((c) => (
              <div key={c.mono} className="flex items-center gap-2.5 border-t py-[9px]" style={{ borderColor: "#F4F4F1" }}>
                <span className="mono min-w-[58px] flex-none text-[10px] font-semibold" style={{ color: "#4B40C4" }}>
                  {c.mono}
                </span>
                <span className="min-w-0 flex-1 text-[12.5px]" style={{ color: "#3A3D44" }}>
                  {c.text}
                </span>
                <svg viewBox="0 0 90 20" preserveAspectRatio="none" className="h-5 w-[56px] flex-none sm:w-[80px]" aria-hidden>
                  <path d={c.path} fill="none" stroke={c.stroke} strokeWidth="1.6" strokeLinecap="round" />
                </svg>
                <ToneChip tone={c.tone}>{c.chip}</ToneChip>
              </div>
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="govern"
          kicker="05 · GOVERN"
          title="Policy governance"
          body="A central policy library with full versioning, review and approval workflows, and audit-ready traceability across the entire lifecycle. Every change, every approval, evidenced and searchable."
          bullets={[
            "Central library with version control",
            "Review and approval trail",
            "Exportable audit trail (CSV)",
          ]}
        >
          <VignetteCard
            title="Version history · POL-04"
            badge="CURRENT: v4.3"
            badgeTone="green"
            footer="Who changed what, when, and which circular made it necessary."
          >
            {VERSION_ROWS.map((r) => (
              <VignetteRow key={r.mono} {...r} />
            ))}
          </VignetteCard>
        </SplitSection>

        {/* How it works: pipeline strip */}
        <section className="flex flex-col gap-[26px]">
          <div className="flex flex-wrap items-end gap-7">
            <h2 className="serif m-0 min-w-[280px] flex-1 text-[32px] font-medium leading-[1.1] tracking-[-0.02em] sm:min-w-[320px] md:text-[42px]">
              How it works
            </h2>
            <p className="m-0 min-w-[280px] flex-1 text-[15.5px] leading-[1.65] sm:min-w-[320px]" style={{ color: "#5B5E66" }}>
              One pipeline, four stages. What the regulator publishes on Monday is owned, mapped
              work in your register the same day.
            </p>
          </div>
          <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map((s, i) => (
              <div
                key={s.step}
                className="anim-rise relative flex flex-col gap-2.5 rounded-[18px] border bg-white p-5"
                style={{ borderColor: "#EAE9E5", animationDelay: `${i * 0.07}s` }}
              >
                <span className="mono text-[10.5px] font-semibold tracking-[.12em]" style={{ color: "#4B40C4" }}>
                  {s.step}
                </span>
                <div className="text-[16px] font-bold leading-tight tracking-[-0.01em]" style={{ color: "#15161B" }}>
                  {s.title}
                </div>
                <div className="text-pretty text-[13px] leading-relaxed" style={{ color: "#71757E" }}>
                  {s.body}
                </div>
                {i < PIPELINE.length - 1 && (
                  <span
                    aria-hidden
                    className="absolute -right-[13px] top-1/2 z-10 hidden -translate-y-1/2 text-[15px] lg:block"
                    style={{ color: "#B6B9BF" }}
                  >
                    →
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Copilot */}
        <SplitSection
          kicker="ASK POLICYAI"
          title="A copilot that answers with the paragraph attached"
          body="Retrieval runs over your policy library and the regulator corpus together, grounded in your org's live compliance state. Every claim is traceable back to the source paragraph."
          bullets={[
            "Grounded in your live obligations, gaps and controls",
            "Citations to circular and policy paragraphs on every answer",
            "Drafts impact assessments for new circulars",
          ]}
          cta={{ label: "Ask it something on day one", href: "/login" }}
        >
          <VignetteCard title="PolicyAI Copilot" badge="CITED" badgeTone="indigo">
            <div className="flex flex-col gap-3 pt-1">
              <div
                className="max-w-[85%] self-end rounded-[14px] rounded-br-[4px] px-3.5 py-2.5 text-[12.5px] font-semibold text-white"
                style={{ background: "#4B40C4" }}
              >
                Which of our policies fail the new digital lending disclosure rules?
              </div>
              <div
                className="max-w-[92%] self-start rounded-[14px] rounded-bl-[4px] border px-3.5 py-2.5"
                style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}
              >
                <div className="text-[12.5px] leading-relaxed" style={{ color: "#3A3D44" }}>
                  Three policies fall short of the key-fact-statement requirement. POL-04 §2.1
                  references the older cooling-off text and has no pre-disbursal disclosure clause.
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {CITATIONS.map((c) => (
                    <CitationChip key={c}>{c}</CitationChip>
                  ))}
                </div>
              </div>
            </div>
          </VignetteCard>
        </SplitSection>

        {/* Knowledge graph foundation band */}
        <section
          id="graph"
          className="flex scroll-mt-24 flex-wrap items-center gap-9 rounded-3xl p-8 sm:p-11 md:p-12"
          style={{ background: "#15161B", color: "#F5F4F2" }}
        >
          <div className="min-w-[280px] flex-1 sm:min-w-[300px]">
            <span className="mono text-[11px] font-semibold tracking-[.14em]" style={{ color: "#8B7DFF" }}>
              FOUNDATION
            </span>
            <h2 className="serif mb-0 mt-2.5 text-[28px] font-medium leading-[1.12] tracking-[-0.02em] md:text-[34px]">
              Everything above runs on the knowledge graph
            </h2>
            <p className="mb-0 mt-3 max-w-[52ch] text-[14.5px] leading-[1.65]" style={{ color: "#9AA0AB" }}>
              2,800+ nodes: regulations, regulators, entity classes, topics, parent acts and
              deadlines, with amends, supersedes and applies-to edges kept live.
            </p>
          </div>
          <Link
            href="/graph"
            className="rounded-[13px] px-6 py-[15px] text-[15px] font-semibold text-white no-underline"
            style={{ background: "#4B40C4" }}
          >
            Open the live graph <span aria-hidden>→</span>
          </Link>
        </section>

        <CtaBand
          title="See your compliance posture in one place"
          body="Join the compliance teams who turn regulatory change into action, without the spreadsheets."
        />
      </main>
    </MarketingShell>
  );
}
