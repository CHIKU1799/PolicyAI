import type { Metadata } from "next";
import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import CopilotHero3D from "@/components/marketing/CopilotHero3D";
import { Chip, Cta } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "PolicyAI Copilot now drafts impact assessments — PolicyAI Blog",
  description:
    "Pick a regulation, get an analyst-grade first pass: applicability, severity, the requirements that bite hardest, and prioritized actions.",
};

function P({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-4 text-[15px] leading-[1.75]" style={{ color: "#3A3D44" }}>
      {children}
    </p>
  );
}

function H2({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="mb-3 mt-9 text-[26px] font-medium leading-snug"
      style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
    >
      {children}
    </h2>
  );
}

export default function CopilotBlogPost() {
  return (
    <MarketingShell>
      <article className="px-5 pb-6 pt-12">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-3 flex items-center justify-center gap-2 text-[12px]" style={{ color: "#71757E" }}>
            <Chip>PRODUCT</Chip>
            <span>July 2026</span>
            <span>·</span>
            <span>5 min read</span>
          </div>
          <h1
            className="text-[40px] font-medium leading-[1.1] tracking-tight md:text-[52px]"
            style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
          >
            The Copilot now drafts
            <br />
            impact assessments{" "}
            <em style={{ color: "#1E5EF6" }}>automatically</em>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed" style={{ color: "#54565E" }}>
            Pick any regulation in the corpus. Thirty seconds later you have an analyst-grade first
            pass: applicability, impact severity, the requirements that bite hardest, and
            prioritized next actions, grounded in your firm&apos;s own profile.
          </p>
        </div>

        <CopilotHero3D />

        <div className="mx-auto max-w-2xl pt-6">
          <H2>The three-week triage problem</H2>
          <P>
            When a master direction lands, someone on the compliance team owns the worst document
            of the quarter: read 60 pages, decide whether it applies, list what it demands, guess
            what it breaks, and circulate a memo before the board asks. Done honestly, that first
            pass takes days per document. Multiply by the regulator&apos;s publishing pace and triage
            becomes the job.
          </P>
          <P>
            The uncomfortable part is that most of that first pass is mechanical. Does this apply
            to an NBFC-MFI? Which requirements are new? Which of our policies do they touch? Those
            are retrieval questions, and retrieval is exactly what a knowledge graph is for.
          </P>

          <H2>What the Copilot actually does</H2>
          <P>
            PolicyAI has already read the document by the time you ask. Every circular in the
            corpus is extracted into discrete requirements with citations, linked in the graph to
            entity classes, topics and deadlines. When you request an impact assessment, the
            Copilot pulls the regulation&apos;s extracted requirements, reads them against your firm&apos;s
            profile (your entity classes, your business topics, your regulators), and drafts a
            structured assessment:
          </P>
          <ul className="mb-4 space-y-2 pl-1">
            {[
              ["Applicability", "whether and why this regulation applies to your firm, in plain language"],
              ["Impact severity", "critical to low, judged for your firm, not in the abstract"],
              ["Affected areas", "the business lines and policy domains the document touches"],
              ["Hardest requirements", "the 3-7 clauses that will actually cost you effort"],
              ["Suggested actions", "concrete steps, each tagged immediate, short-term, or monitor"],
            ].map(([t, d]) => (
              <li key={t} className="flex gap-3 text-[14.5px]" style={{ color: "#3A3D44" }}>
                <span
                  className="mt-1 h-2 w-2 flex-none rounded-full"
                  style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
                />
                <span>
                  <strong style={{ color: "#15254E" }}>{t}:</strong> {d}
                </span>
              </li>
            ))}
          </ul>

          <div
            className="mb-4 rounded-2xl border p-5 text-[13.5px] leading-relaxed"
            style={{ borderColor: "#E4E0F7", background: "#F8F7FE", color: "#3A3D44" }}
          >
            <div className="mb-1 text-[11px] font-bold uppercase tracking-wide" style={{ color: "#1746D6" }}>
              From a real draft, RBI (NBFC-MFI) Directions
            </div>
            &ldquo;The firm is an NBFC-MFI and therefore subject to these Directions. The firm must
            maintain a minimum of 60 percent of total assets deployed towards microfinance loans,
            maintain a capital adequacy ratio of not less than 15 percent, and establish
            Board-approved internal exposure limits… overall severity: <strong>high</strong>.&rdquo;
          </div>

          <H2>A first pass, not a verdict</H2>
          <P>
            The draft is deliberately labelled an analyst first pass. Every statement is grounded
            in the extracted requirements: the model is instructed not to invent obligations, and
            the assessment links back to the source document so a compliance officer can verify
            any line in one click. You review, edit, and own the judgement; the Copilot owns the
            reading.
          </P>
          <P>
            That division of labour is the point. The teams we build for do not want an oracle;
            they want the three mechanical days back so the judgement call gets the attention it
            deserves.
          </P>

          <H2>Where to find it</H2>
          <P>
            Open the Copilot, use the &ldquo;Draft an impact assessment&rdquo; panel, search any regulation in
            the corpus, and press Draft. It works today for every document PolicyAI has ingested,
            across RBI, SEBI and IRDAI, and every new circular the crawlers pick up becomes
            assessable the moment it lands in the graph.
          </P>
          <p className="mt-6 text-[14px]">
            <Link href="/login" className="font-semibold no-underline" style={{ color: "#1746D6" }}>
              Try it on your firm&apos;s profile →
            </Link>
          </p>
        </div>
      </article>

      <Cta
        title="An analyst that reads every rule"
        body="So your team spends its time on judgement calls, not reading PDFs."
      />
    </MarketingShell>
  );
}
