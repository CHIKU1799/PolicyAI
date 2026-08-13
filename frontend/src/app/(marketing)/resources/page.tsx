import type { Metadata } from "next";
import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import {
  ACCENT,
  BODY,
  CtaBand,
  FAINT,
  GREEN,
  INK,
  Kicker,
  LINE,
  MUTED,
  PageHero,
} from "@/components/marketing/mkt2/ui";

export const metadata: Metadata = {
  title: "Resources · PolicyAI",
  description:
    "The regulators we monitor, a live product walkthrough, guides for compliance teams, the blog and the changelog.",
};

// The real monitored source list (docs/PLATFORM_GUIDE.md §1).
const REGULATORS: { name: string; scope: string; status: "live" | "soon" }[] = [
  { name: "RBI", scope: "Notifications and press releases", status: "live" },
  { name: "SEBI", scope: "Circulars and master circulars", status: "live" },
  { name: "IRDAI", scope: "Circulars and product norms", status: "live" },
  { name: "MCA", scope: "Corporate-law notifications", status: "live" },
  { name: "PIB", scope: "Government press coverage", status: "live" },
  { name: "CERT-In", scope: "Cyber directions and advisories", status: "live" },
  { name: "PFRDA", scope: "Pension-sector circulars", status: "live" },
  { name: "IFSCA", scope: "GIFT City regulations", status: "live" },
  { name: "FIU-IND", scope: "AML/CFT communications", status: "live" },
  { name: "NPCI", scope: "Activates with OCR (scanned PDFs)", status: "soon" },
  { name: "DGFT", scope: "Activates with OCR (scanned PDFs)", status: "soon" },
];

const GUIDES = [
  {
    title: "From circular to closed gap in one week",
    body: "How a compliance team runs the full loop: a new RBI circular lands, becomes obligations, gets diffed against the firm's policies, and ends as owned, dated remediation tasks.",
    tag: "WORKFLOW GUIDE",
  },
  {
    title: "Reading your gap analysis like an auditor",
    body: "What 4-state coverage means, how severity triage works, and how to use the cited regulation passages as evidence when the inspector asks why a gap was closed.",
    tag: "PRACTITIONER GUIDE",
  },
  {
    title: "Choosing an LLM setup your risk team will sign off",
    body: "Frontier versus open-weight models for regulatory work, what org-keyed caching changes, and when an on-prem deployment is worth it.",
    tag: "BUYER GUIDE",
  },
];

// Real shipped work, kept from the operator changelog.
const CHANGELOG = [
  ["Jul 2026", "Copilot drafts impact assessments; structured answers with cited sources"],
  ["Jul 2026", "Per-firm workspaces: every signup gets an isolated organization"],
  ["Jul 2026", "Operator fault checks: crawler freshness, mapping backlog, embedding coverage"],
  ["Jul 2026", "Knowledge-graph explorer: search, hop depth, node inspection"],
  ["Jul 2026", "Control-failure alerts raised at the database layer; 12-week pass-rate trends"],
  ["Jun 2026", "Bitemporal timeline: ask what the rules were as of any date"],
  ["Jun 2026", "Deep archive backfill for RBI and SEBI, beyond the current listing page"],
];

export default function ResourcesPage() {
  return (
    <MarketingShell>
      <main className="mx-auto flex max-w-[1304px] flex-col gap-16 px-5 pb-24 pt-12 md:gap-24 md:px-8 md:pt-16">
        <PageHero
          kicker="RESOURCES"
          title="Learn the system before you buy it"
          lede="The regulators we watch, a live walkthrough of the product, guides for compliance teams, and a plain record of what shipped."
        />

        {/* Featured: graph + blog */}
        <section id="docs" className="grid scroll-mt-24 gap-4 lg:grid-cols-2">
          {/* Journey card (dark, links to the landing journey band). */}
          <Link
            href="/#journey"
            className="anim-rise group flex flex-col justify-between gap-8 rounded-[20px] p-6 no-underline md:p-7"
            style={{ background: "#15161B", color: "#F5F4F2" }}
          >
            <div>
              <span className="mono text-[10.5px] font-semibold tracking-[.16em]" style={{ color: "#8A8FA0" }}>
                LIVE WALKTHROUGH
              </span>
              <h2 className="serif mb-0 mt-2.5 text-[26px] font-medium leading-[1.15] tracking-[-0.02em] md:text-[30px]">
                Watch a circular become audit-ready
              </h2>
              <p className="mb-0 mt-3 max-w-[52ch] text-[13.5px] leading-relaxed" style={{ color: "#A7ABB4" }}>
                One RBI circular, followed end to end: published at 09:04, matched to your firm by
                09:06, an obligation with owner and deadline by lunch, and a tested control with
                citable evidence by Friday. The walkthrough is live on our landing page.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {["ALERT", "OBLIGATION", "GAP → OWNER", "CONTROL ✓"].map((e) => (
                <span
                  key={e}
                  className="mono rounded-md border px-2 py-1 text-[10px]"
                  style={{ borderColor: "#34363F", color: "#B9BDC7" }}
                >
                  {e}
                </span>
              ))}
              <span className="ml-auto text-[13.5px] font-semibold transition-transform group-hover:translate-x-1" style={{ color: "#B7AEF9" }}>
                See the walkthrough →
              </span>
            </div>
          </Link>

          {/* Blog card (the post that exists). */}
          <Link
            href="/blog/copilot-impact-assessments"
            className="anim-rise group flex flex-col justify-between gap-8 rounded-[20px] border bg-white p-6 no-underline transition-shadow hover:shadow-[0_14px_30px_-14px_rgba(17,18,27,.25)] md:p-7"
            style={{ borderColor: LINE }}
          >
            <div>
              <span className="mono text-[10.5px] font-semibold tracking-[.16em]" style={{ color: ACCENT }}>
                FROM THE BLOG
              </span>
              <h2 className="serif mb-0 mt-2.5 text-[26px] font-medium leading-[1.15] tracking-[-0.02em]" style={{ color: INK }}>
                The Copilot now drafts impact assessments
              </h2>
              <p className="mb-0 mt-3 max-w-[52ch] text-[13.5px] leading-relaxed" style={{ color: BODY }}>
                Pick a regulation and get an analyst-grade first pass: applicability, severity, the
                requirements that bite hardest, and prioritized actions. Grounded in your firm&apos;s
                profile, ready for human review.
              </p>
            </div>
            <span className="text-[13.5px] font-semibold transition-transform group-hover:translate-x-1" style={{ color: ACCENT }}>
              Read the post →
            </span>
          </Link>
        </section>

        {/* Regulators grid */}
        <section className="flex flex-col gap-6">
          <div className="flex flex-wrap items-end gap-7">
            <div className="min-w-[260px] flex-1">
              <Kicker>COVERAGE</Kicker>
              <h2 className="serif mb-0 mt-2.5 text-[28px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[36px]">
                Regulators we monitor
              </h2>
            </div>
            <p className="m-0 min-w-[260px] flex-1 text-[14px] leading-relaxed" style={{ color: BODY }}>
              The crawler runs every 6 hours across every enabled source, with per-source cadence
              enforced internally and deep archive backfill behind it. You can also trigger a scan on
              demand from the dashboard.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {REGULATORS.map((r, i) => (
              <div
                key={r.name}
                className="anim-rise flex flex-col gap-1.5 rounded-[16px] border bg-white p-4"
                style={{ borderColor: LINE, animationDelay: `${i * 0.03}s` }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[15px] font-bold tracking-[-0.01em]" style={{ color: INK }}>
                    {r.name}
                  </span>
                  <span
                    className="mono rounded-md px-1.5 py-0.5 text-[9px] font-semibold tracking-[.08em]"
                    style={
                      r.status === "live"
                        ? { background: "#E8F6EE", color: GREEN }
                        : { background: "#FFF3E6", color: "#E0683C" }
                    }
                  >
                    {r.status === "live" ? "EVERY 6H" : "WIRED"}
                  </span>
                </div>
                <span className="text-[12px] leading-snug" style={{ color: MUTED }}>
                  {r.scope}
                </span>
              </div>
            ))}
          </div>
          <p className="m-0 text-[12.5px]" style={{ color: FAINT }}>
            Exchange and depository circulars (NSE, BSE, NSDL, CDSL) are on the roadmap. CBDT, CBIC
            and eGazette content arrives indirectly through PIB and gazette coverage.
          </p>
        </section>

        {/* Guides */}
        <section className="flex flex-col gap-6">
          <div className="text-center">
            <Kicker>GUIDES</Kicker>
            <h2 className="serif mb-0 mt-2.5 text-[28px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[36px]">
              Walkthroughs, given live
            </h2>
            <p className="mx-auto mb-0 mt-3 max-w-[56ch] text-[14px] leading-relaxed" style={{ color: BODY }}>
              We do not do gated PDFs. Each guide is a working session on the live platform, on your
              segment&apos;s regulations, with your questions.
            </p>
          </div>
          <div className="grid gap-3.5 md:grid-cols-3">
            {GUIDES.map((g, i) => (
              <Link
                key={g.title}
                href="/contact?intent=demo"
                className="anim-rise flex flex-col gap-2.5 rounded-[18px] border bg-white p-5 no-underline transition-[box-shadow,transform] duration-300 hover:-translate-y-[3px] hover:shadow-[0_14px_30px_-14px_rgba(17,18,27,.25)]"
                style={{ borderColor: LINE, animationDelay: `${i * 0.06}s` }}
              >
                <span className="mono text-[10.5px] font-semibold tracking-[.12em]" style={{ color: ACCENT }}>
                  {g.tag}
                </span>
                <span className="text-[16.5px] font-bold leading-snug tracking-[-0.01em]" style={{ color: INK }}>
                  {g.title}
                </span>
                <span className="text-pretty text-[13px] leading-relaxed" style={{ color: MUTED }}>
                  {g.body}
                </span>
                <span className="mt-auto pt-2 text-[13px] font-semibold" style={{ color: ACCENT }}>
                  Get the guide, live →
                </span>
              </Link>
            ))}
          </div>
        </section>

        {/* Changelog + status */}
        <section id="changelog" className="grid scroll-mt-24 gap-4 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-[20px] border bg-white p-6 md:p-7" style={{ borderColor: LINE }}>
            <Kicker>CHANGELOG</Kicker>
            <h2 className="serif mb-0 mt-2 text-[24px] font-medium tracking-[-0.02em]" style={{ color: INK }}>
              What shipped
            </h2>
            <ul className="m-0 mt-4 list-none p-0">
              {CHANGELOG.map(([when, what]) => (
                <li key={what} className="flex gap-4 border-t py-2.5" style={{ borderColor: "#F4F4F1" }}>
                  <span className="mono w-20 flex-none pt-0.5 text-[11px]" style={{ color: FAINT }}>
                    {when}
                  </span>
                  <span className="text-[13px] leading-relaxed" style={{ color: "#3A3D44" }}>
                    {what}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col gap-4">
            <div id="status" className="scroll-mt-24 rounded-[20px] border bg-white p-6" style={{ borderColor: LINE }}>
              <div className="flex items-center gap-3">
                <span className="h-2.5 w-2.5 flex-none animate-pulse rounded-full" style={{ background: GREEN }} />
                <span className="text-[14.5px] font-bold" style={{ color: INK }}>
                  All systems monitored
                </span>
              </div>
              <p className="mb-0 mt-2.5 text-[12.5px] leading-relaxed" style={{ color: MUTED }}>
                Crawler freshness, ingestion throughput, mapping backlog and alert flow are checked
                continuously by the PolicyAI operations team.
              </p>
            </div>
            <div className="flex flex-1 flex-col justify-between gap-4 rounded-[20px] border bg-white p-6" style={{ borderColor: LINE }}>
              <div>
                <Kicker>STAY CURRENT</Kicker>
                <p className="mb-0 mt-2.5 text-[13.5px] leading-relaxed" style={{ color: BODY }}>
                  Want a monthly note on what changed across RBI, SEBI and IRDAI, and what shipped in
                  PolicyAI? Ask and we will add you; no forms, no drip sequence.
                </p>
              </div>
              <Link
                href="/contact"
                className="inline-block rounded-[12px] border px-4 py-2.5 text-center text-[13px] font-semibold no-underline"
                style={{ borderColor: LINE, color: INK, background: "#fff" }}
              >
                Ask for the monthly update
              </Link>
            </div>
          </div>
        </section>

        <CtaBand
          title="The best resource is the product itself"
          body="Sign up and read your own obligations register, or book a session and we will drive on your segment's regulations."
          primary={{ label: "Start free", href: "/login" }}
          secondary={{ label: "Book a walkthrough", href: "/contact?intent=demo" }}
        />
      </main>
    </MarketingShell>
  );
}
