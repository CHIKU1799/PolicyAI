import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import { sparkPath } from "@/components/marketing/DashboardMock";
import {
  CitationChip,
  CtaBand,
  PageHero,
  SplitSection,
  ToneChip,
  VignetteCard,
  VignetteRow,
} from "@/components/marketing/PageSections";

export const metadata: Metadata = {
  title: "Solutions · PolicyAI",
  description: "By-persona value for NBFCs, small banks, AIFs and fintech founders.",
};

const NBFC_ROWS = [
  { mono: "OBL-2210", text: "SBR exposure norms: single-borrower review", chip: "High", tone: "red" as const },
  { mono: "OBL-2214", text: "KYC Master Direction: re-KYC cadence update", chip: "Medium", tone: "amber" as const },
  { mono: "OBL-1044", text: "Digital lending: key-fact statement", chip: "High", tone: "red" as const },
  { mono: "OBL-2231", text: "Grievance escalation matrix publication", chip: "Mapped", tone: "green" as const },
];

const BANK_KPIS = [
  { label: "Controls passing", value: "91%", tone: "green" as const, stroke: "#1F9D5B", path: sparkPath(22, true) },
  { label: "Gaps closed (30d)", value: "37", tone: "green" as const, stroke: "#1F9D5B", path: sparkPath(33, true) },
  { label: "Overdue tasks", value: "4", tone: "amber" as const, stroke: "#E0683C", path: sparkPath(44, false) },
];

const AIF_ROWS = [
  { mono: "May 26", text: "Valuation timelines amended", chip: "AMENDS", tone: "indigo" as const },
  { mono: "Nov 25", text: "Quarterly reporting format revised", chip: "AMENDS", tone: "indigo" as const },
  { mono: "Jun 25", text: "Master circular for AIFs reissued", chip: "SUPERSEDES", tone: "amber" as const },
];

const FINTECH_CITATIONS = ["RBI PA/PG Guidelines ¶3", "CERT-In Directions 2022", "DPDP Act §7"];

const COMPARISON = [
  {
    aspect: "Change detection",
    before: "Someone reads the regulator sites on Friday",
    after: "Every source crawled every 6 hours, severity-scored alerts",
  },
  {
    aspect: "Obligations",
    before: "Excel tabs per regulation, one owner who knows them",
    after: "A structured register mapped to your profile, with citations",
  },
  {
    aspect: "Gap evidence",
    before: "Assembled in the week before the audit",
    after: "The exact policy passage attached as you work",
  },
  {
    aspect: "Controls",
    before: "An annual sample test in a shared folder",
    after: "Pass-rate trends, with alerts the moment one fails",
  },
  {
    aspect: "Audit trail",
    before: "Email archaeology",
    after: "Versioned, approved and exportable",
  },
];

export default function SolutionsPage() {
  return (
    <MarketingShell>
      <main className="mx-auto flex max-w-[1304px] flex-col gap-16 px-5 pb-24 pt-12 md:gap-[88px] md:px-8 md:pt-16">
        <PageHero
          kicker="SOLUTIONS"
          title={
            <>
              Built for the people
              <br />
              who own the obligation
            </>
          }
          lede="The same platform, tuned by entity class: PolicyAI's knowledge graph knows which rules apply to which kind of firm, so every dashboard starts relevant."
        />

        <SplitSection
          id="nbfc"
          kicker="NBFC COMPLIANCE HEAD"
          title="Scale-based regulation, without the spot-checks"
          body="A Middle-Layer NBFC lives under layer-specific prudential norms, a KYC Master Direction that keeps moving, and an RBI cadence that lands something new every week. Today the tracker is a spreadsheet, and the person who maintains it is the single point of failure."
          bullets={[
            "Obligations mapped to your entity profile, incl. NBFC-MFI, with severity and the circular paragraph attached",
            "Horizon alerts within hours of publication: the crawler runs every 6 hours",
            "Gap analysis against your own Fair Practices Code and KYC policy, with citable evidence",
          ]}
          cta={{ label: "Start with your profile", href: "/login" }}
          anchors={["mfi"]}
        >
          <VignetteCard
            title="Obligations · NBFC profile"
            badge="139+ MATCHED"
            badgeTone="indigo"
            footer="139+ RBI regulations auto-matched to a single NBFC profile, filterable and exportable."
          >
            {NBFC_ROWS.map((r) => (
              <VignetteRow key={r.mono} {...r} />
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="bank"
          kicker="SMALL BANK / SFB CCO"
          title="Board visibility without the quarter-end scramble"
          body="The quarterly board and ACB compliance report is the CCO's single biggest recurring task, assembled by hand from inboxes and branch spreadsheets, while inspection readiness hangs on evidence someone can actually find."
          bullets={[
            "Coverage wider than the usual BFSI set: RBI, SEBI, IRDAI, FIU-IND, CERT-In and more",
            "Copilot answers “what changed for us this quarter” with citations: board-pack raw material",
            "Controls testing with 12-week pass-rate trends and instant failure alerts",
          ]}
          cta={{ label: "See the dashboard", href: "/login" }}
          anchors={["insurer"]}
          flip
        >
          <VignetteCard
            title="Quarter at a glance"
            badge="● LIVE"
            badgeTone="green"
            footer="Real deltas from live data, not a snapshot pasted the night before the board meets."
          >
            {BANK_KPIS.map((k) => (
              <div key={k.label} className="flex items-center gap-2.5 border-t py-[9px]" style={{ borderColor: "#F4F4F1" }}>
                <span className="min-w-0 flex-1 text-[12.5px]" style={{ color: "#3A3D44" }}>
                  {k.label}
                </span>
                <svg viewBox="0 0 90 20" preserveAspectRatio="none" className="h-5 w-[56px] flex-none sm:w-[80px]" aria-hidden>
                  <path d={k.path} fill="none" stroke={k.stroke} strokeWidth="1.6" strokeLinecap="round" />
                </svg>
                <ToneChip tone={k.tone}>{k.value}</ToneChip>
              </div>
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="aif"
          kicker="AIF / FUND OPERATIONS"
          title="SEBI's amendment stream, consolidated"
          body="A Cat II AIF runs compliance with a three-person ops team and a CS on retainer, against master circulars that are amended constantly and consolidate painfully. Outside counsel bills by the question."
          bullets={[
            "SEBI circulars and master circulars, deep archive included, with amends and supersedes edges kept live",
            "Copilot with citations replaces half the quick questions to outside counsel",
            "Self-serve and free during early access: no enterprise sales cycle",
          ]}
          cta={{ label: "Explore the SEBI corpus", href: "/login" }}
        >
          <VignetteCard
            title="Lineage · AIF Master Circular"
            badge="1,600+ IN CORPUS"
            badgeTone="indigo"
            footer="1,600+ SEBI circulars staged, every amendment edge queryable in the graph."
          >
            {AIF_ROWS.map((r) => (
              <VignetteRow key={r.text} {...r} />
            ))}
          </VignetteCard>
        </SplitSection>

        <SplitSection
          id="fintech"
          kicker="FINTECH FOUNDER"
          title="License-ready before the license"
          body="Pre-authorisation, the rules already bind you: DPDP and CERT-In apply today, and the PA or NBFC application expects governance you have not built yet. Law-firm memos answer one question at a time, a week later."
          bullets={[
            "Explore what applies to a payment aggregator or NBFC in the knowledge graph, before you are one",
            "CERT-In directions and DPDP developments already in the monitored corpus",
            "Copilot answers, with citations, in language a non-compliance founder can read",
          ]}
          cta={{ label: "Ask your first question", href: "/login" }}
          anchors={["pa"]}
          flip
        >
          <VignetteCard title="PolicyAI Copilot" badge="CITED" badgeTone="indigo">
            <div className="flex flex-col gap-3 pt-1">
              <div
                className="max-w-[85%] self-end rounded-[14px] rounded-br-[4px] px-3.5 py-2.5 text-[12.5px] font-semibold text-white"
                style={{ background: "#4B40C4" }}
              >
                What must be true before we apply for PA authorisation?
              </div>
              <div
                className="max-w-[92%] self-start rounded-[14px] rounded-bl-[4px] border px-3.5 py-2.5"
                style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}
              >
                <div className="text-[12.5px] leading-relaxed" style={{ color: "#3A3D44" }}>
                  Net-worth thresholds, governance and IT requirements apply at application; escrow
                  and merchant-KYC obligations bind from day one of operations.
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {FINTECH_CITATIONS.map((c) => (
                    <CitationChip key={c}>{c}</CitationChip>
                  ))}
                </div>
              </div>
            </div>
          </VignetteCard>
        </SplitSection>

        {/* Comparison strip */}
        <section className="flex flex-col gap-[26px]">
          <div className="flex flex-wrap items-end gap-7">
            <h2 className="serif m-0 min-w-[280px] flex-1 text-[32px] font-medium leading-[1.1] tracking-[-0.02em] sm:min-w-[320px] md:text-[42px]">
              The spreadsheet, retired
            </h2>
            <p className="m-0 min-w-[280px] flex-1 text-[15.5px] leading-[1.65] sm:min-w-[320px]" style={{ color: "#5B5E66" }}>
              Every persona above runs the same workflow today: a tracker, an inbox, and a scramble.
              Here is what changes.
            </p>
          </div>
          <div className="overflow-hidden rounded-[20px] border bg-white" style={{ borderColor: "#EAE9E5" }}>
            <div
              className="hidden gap-6 border-b px-6 py-[14px] md:grid md:grid-cols-[160px_1fr_1fr]"
              style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}
            >
              <span />
              <span className="mono text-[10.5px] font-semibold tracking-[.12em]" style={{ color: "#9A9DA4" }}>
                SPREADSHEETS &amp; INBOXES
              </span>
              <span className="mono text-[10.5px] font-semibold tracking-[.12em]" style={{ color: "#4B40C4" }}>
                POLICYAI
              </span>
            </div>
            {COMPARISON.map((row, i) => (
              <div
                key={row.aspect}
                className={`grid gap-2 px-5 py-4 md:grid-cols-[160px_1fr_1fr] md:gap-6 md:px-6 ${i > 0 ? "border-t" : ""}`}
                style={{ borderColor: "#F4F4F1" }}
              >
                <div className="text-[13px] font-bold" style={{ color: "#15161B" }}>
                  {row.aspect}
                </div>
                <div className="flex gap-2 text-[13px]" style={{ color: "#71757E" }}>
                  <span aria-hidden style={{ color: "#C0392B" }}>
                    ✕
                  </span>
                  {row.before}
                </div>
                <div className="flex gap-2 text-[13px]" style={{ color: "#3A3D44" }}>
                  <span aria-hidden className="font-bold" style={{ color: "#1F9D5B" }}>
                    ✓
                  </span>
                  {row.after}
                </div>
              </div>
            ))}
          </div>
        </section>

        <CtaBand
          title="Your segment, already understood"
          body="Sign up, name your firm, and the graph does the rest: applicable regulations, obligations, and gaps against your own policies."
        />
      </main>
    </MarketingShell>
  );
}
