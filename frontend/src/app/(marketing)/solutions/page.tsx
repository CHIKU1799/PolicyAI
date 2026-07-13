import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import { Cta, Hero, Section } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "Solutions — PolicyAI",
  description: "Purpose-built for regulated Indian BFSI segments.",
};

const SEGMENTS = [
  {
    id: "nbfc",
    step: "NBFC",
    title: "For NBFCs",
    body: "Scale-based regulation moved the goalposts: layer-specific prudential norms, governance mandates and disclosure calendars. PolicyAI knows which layer you sit in and maps only what applies.",
    bullets: [
      "SBR framework obligations by layer",
      "Capital adequacy and exposure norms tracked as deadlines",
      "KYC Master Direction amendments flagged the day they land",
    ],
    stat: ["139+", "RBI regulations auto-matched to a single NBFC profile"],
  },
  {
    id: "mfi",
    step: "Microfinance",
    title: "For Microfinance lenders",
    body: "Pricing caps, household-income limits, fair-practices conduct: microfinance rules are granular and enforcement is active. PolicyAI diffs every circular against your own Fair Practices Code.",
    bullets: [
      "Pricing of microfinance loans, tracked clause by clause",
      "Fair Practices Code gap analysis with citable evidence",
      "Qualifying-asset criteria changes surfaced as alerts",
    ],
    stat: ["81+", "obligations mapped for a demo NBFC-MFI in one run"],
  },
  {
    id: "aif",
    step: "AIF & PMS",
    title: "For AIFs & portfolio managers",
    body: "SEBI's circular stream is relentless and slug-addressed. PolicyAI crawls it continuously, extracts the requirements, and keeps your disclosure and valuation calendars honest.",
    bullets: [
      "SEBI circulars and master circulars, deep archive included",
      "Valuation, disclosure and reporting deadlines as first-class objects",
      "Custodian and benchmarking obligations mapped to owners",
    ],
    stat: ["1,600+", "SEBI circulars staged in the corpus"],
  },
  {
    id: "pa",
    step: "Payments",
    title: "For Payment Aggregators & gateways",
    body: "PA/PG guidelines, escrow management, merchant KYC, cyber-resilience: payments compliance spans RBI and NPCI. PolicyAI holds it in one graph so nothing falls between the seams.",
    bullets: [
      "PA/PG authorisation conditions tracked as obligations",
      "Escrow and settlement norms with deadline monitoring",
      "KYC and cyber-security requirements deduplicated across sources",
    ],
    stat: ["16", "monitoring sources configured, 5 live today"],
  },
  {
    id: "insurer",
    step: "Insurance",
    title: "For Insurers",
    body: "IRDAI circulars on product norms, policyholder protection and expenses of management, monitored on cadence and mapped to your product and policy register.",
    bullets: [
      "IRDAI circular crawler live today",
      "Product and conduct obligations by entity class",
      "Board-reporting requirements with due dates",
    ],
    stat: ["24x7", "continuous monitoring with severity-scored alerts"],
  },
];

export default function SolutionsPage() {
  return (
    <MarketingShell>
      <Hero
        eyebrow="SOLUTIONS"
        title={
          <>
            Built for the segments
            <br />
            regulators watch closest
          </>
        }
        lede="The same platform, tuned by entity class: PolicyAI's knowledge graph knows which rules apply to which kind of firm, so every dashboard starts relevant."
      />
      {SEGMENTS.map((s, i) => (
        <Section key={s.id} id={s.id} step={s.step} title={s.title} body={s.body} bullets={s.bullets} flip={i % 2 === 1}>
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div
              className="text-[44px] font-medium"
              style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
            >
              {s.stat[0]}
            </div>
            <div className="max-w-[220px] text-[12px]" style={{ color: "#71757E" }}>
              {s.stat[1]}
            </div>
          </div>
        </Section>
      ))}
      <Cta
        title="Your segment, already understood"
        body="Sign up, name your firm, and the graph does the rest: applicable regulations, obligations, and gaps against your own policies."
      />
    </MarketingShell>
  );
}
