import type { Metadata } from "next";
import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import {
  ACCENT,
  BODY,
  CheckItem,
  CtaBand,
  FAINT,
  Faq,
  GREEN,
  INK,
  Kicker,
  LINE,
  MUTED,
  PageHero,
  TrustStrip,
} from "@/components/marketing/mkt2/ui";

export const metadata: Metadata = {
  title: "Pricing · PolicyAI",
  description:
    "Transparent early-access pricing for Indian BFSI compliance teams. Start free, no card required.",
};

const TIERS: {
  name: string;
  price: string;
  period: string;
  blurb: string;
  features: string[];
  cta: string;
  href: string;
  highlight?: boolean;
}[] = [
  {
    name: "Starter",
    price: "₹14,999",
    period: "per month · introductory",
    blurb: "For fintechs and small firms that need to stop missing circulars.",
    features: [
      "1 firm workspace, isolated by design",
      "Continuous monitoring: RBI, SEBI, IRDAI, MCA, PIB, CERT-In, PFRDA, IFSCA, FIU-IND",
      "Obligations register for your entity classes",
      "PolicyAI Copilot with citations",
      "Knowledge graph explorer",
      "Up to 3 team seats",
    ],
    cta: "Start free",
    href: "/login",
  },
  {
    name: "Growth",
    price: "₹49,999",
    period: "per month · introductory",
    blurb: "For teams that run compliance on PolicyAI every week.",
    features: [
      "Everything in Starter",
      "Gap analysis against your own policies, with cited evidence",
      "Controls testing with failure alerts and 12-week trends",
      "Policy library with versions and owners",
      "Tasks and remediation workflows",
      "Up to 15 team seats with admin roles",
      "Priority source requests and priority support",
    ],
    cta: "Talk to us",
    href: "/contact?intent=sales",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "annual agreement",
    blurb: "For groups, multiple entities, and procurement-grade requirements.",
    features: [
      "Everything in Growth",
      "Platform admin console across group entities",
      "SSO-ready security posture and questionnaire support",
      "On-prem LLM option via open-weight models",
      "Unlimited seats",
      "Dedicated onboarding and support",
    ],
    cta: "Talk to sales",
    href: "/contact?intent=sales",
  },
];

// Comparison rows grounded in the real feature set (docs/PLATFORM_GUIDE.md).
// Values: true = included, false = not included, string = qualified.
const COMPARE: { row: string; tiers: [boolean | string, boolean | string, boolean | string] }[] = [
  { row: "Regulatory monitoring, 9 sources crawled every 6 hours", tiers: [true, true, true] },
  { row: "Compliance dashboard with Horizon feed and posture score", tiers: [true, true, true] },
  { row: "On-demand scans (new items appear in minutes)", tiers: [true, true, true] },
  { row: "Obligations register, filterable and exportable", tiers: [true, true, true] },
  { row: "Knowledge graph explorer", tiers: [true, true, true] },
  { row: "PolicyAI Copilot with citations", tiers: [true, true, true] },
  { row: "Policy document uploads (Knowledge Base)", tiers: [false, true, true] },
  { row: "Gap analysis vs your own policies, 4-state coverage", tiers: [false, true, true] },
  { row: "Controls testing with failure alerts", tiers: [false, true, true] },
  { row: "Tasks and remediation workflows", tiers: [false, true, true] },
  { row: "Team seats", tiers: ["Up to 3", "Up to 15", "Unlimited"] },
  { row: "Priority source requests", tiers: [false, true, true] },
  { row: "Platform admin console for group entities", tiers: [false, false, true] },
  { row: "On-prem LLM via open-weight models", tiers: [false, false, true] },
  { row: "Support", tiers: ["Email", "Priority", "Dedicated"] },
];

const FAQS = [
  {
    q: "Is our data isolated from other firms?",
    a: "Yes. Every signup provisions its own workspace, and Postgres row-level security is enforced with your session token on every org-scoped table. Your documents live in a private storage bucket that only server-side code can read. Isolation is a database property, not a UI setting.",
  },
  {
    q: "Which regulators do you cover?",
    a: "RBI (notifications and press releases), SEBI (circulars and master circulars), IRDAI, MCA, PIB, CERT-In, PFRDA, IFSCA and FIU-IND are monitored today. NPCI and DGFT are wired and activate with OCR, since they publish scanned PDFs. Exchange and depository circulars are on the roadmap.",
  },
  {
    q: "How quickly do new circulars show up?",
    a: "The crawler runs every 6 hours across all enabled sources, and you can trigger an on-demand scan from the dashboard at any time; new items appear as alerts within minutes of a scan, scored for severity against your profile.",
  },
  {
    q: "Can we cancel?",
    a: "Yes, any time on monthly plans, and your obligations register stays exportable so you never lose the record. There is no card required to start, and no lock-in on the trial.",
  },
  {
    q: "Do you train AI models on our data?",
    a: "No. Your policies and documents are never used to train models. They are processed to map obligations and answer your questions, results are cached per organization, and nothing derived from your data is visible to any other firm.",
  },
  {
    q: "Which LLM providers do you use?",
    a: "The platform is provider-switchable: it runs on Anthropic models today and can run on open-weight models (GLM, Kimi, gpt-oss and others) where cost or data-control requirements demand it. Enterprise plans can deploy an open-weight model on your own infrastructure.",
  },
];

function CellValue({ v }: { v: boolean | string }) {
  if (v === true)
    return (
      <span aria-label="Included" className="font-bold" style={{ color: GREEN }}>
        ✓
      </span>
    );
  if (v === false)
    return (
      <span aria-label="Not included" style={{ color: "#C9CBD0" }}>
        ·
      </span>
    );
  return (
    <span className="text-[12px] font-semibold" style={{ color: "#3A3D44" }}>
      {v}
    </span>
  );
}

export default function PricingPage() {
  return (
    <MarketingShell>
      <main className="mx-auto flex max-w-[1304px] flex-col gap-16 px-5 pb-24 pt-12 md:gap-24 md:px-8 md:pt-16">
        <PageHero
          kicker="EARLY ACCESS PRICING"
          title="A price you can see before the first call"
          lede="Almost every compliance vendor in India is quote-only. We publish our numbers: introductory early-access pricing, every tier on the full regulatory corpus, and you never pay per regulation."
        />

        {/* Tiers */}
        <section className="flex flex-col gap-6">
          <div className="grid items-stretch gap-4 lg:grid-cols-3">
            {TIERS.map((t) => (
              <div
                key={t.name}
                className={`anim-rise relative flex flex-col gap-4 rounded-[20px] border bg-white p-6 md:p-7 ${
                  t.highlight ? "lg:-translate-y-3" : ""
                }`}
                style={
                  t.highlight
                    ? {
                        borderColor: ACCENT,
                        boxShadow: "0 24px 54px -20px rgba(75,64,196,.38)",
                      }
                    : { borderColor: LINE }
                }
              >
                {t.highlight && (
                  <span
                    className="mono absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full px-3.5 py-1 text-[10px] font-bold tracking-[.14em] text-white"
                    style={{ background: ACCENT }}
                  >
                    RECOMMENDED
                  </span>
                )}
                <div>
                  <Kicker>{t.name.toUpperCase()}</Kicker>
                  <div className="serif mt-2 text-[40px] font-medium leading-none tracking-[-0.02em]" style={{ color: INK }}>
                    {t.price}
                  </div>
                  <div className="mt-1.5 text-[12.5px]" style={{ color: FAINT }}>
                    {t.period}
                  </div>
                </div>
                <p className="m-0 text-[13.5px] leading-relaxed" style={{ color: BODY }}>
                  {t.blurb}
                </p>
                <ul className="m-0 flex list-none flex-col gap-2 p-0">
                  {t.features.map((f) => (
                    <CheckItem key={f}>{f}</CheckItem>
                  ))}
                </ul>
                <Link
                  href={t.href}
                  className="mt-auto block rounded-[14px] py-3.5 text-center text-[14.5px] font-semibold no-underline"
                  style={
                    t.highlight
                      ? { background: ACCENT, color: "#fff", boxShadow: "0 8px 22px rgba(75,64,196,.26)" }
                      : { border: `1px solid ${LINE}`, color: INK, background: "#fff" }
                  }
                >
                  {t.cta}
                </Link>
              </div>
            ))}
          </div>
          <p className="mx-auto m-0 max-w-[70ch] text-center text-[12.5px] leading-relaxed" style={{ color: FAINT }}>
            Introductory early-access numbers while we onboard design partners; they will rise as the
            platform matures, and early customers keep their rate for 12 months. Annual billing gets
            two months free. No card required to start; cancel anytime.
          </p>
        </section>

        {/* Why transparent */}
        <section
          className="flex flex-wrap items-center gap-6 rounded-[20px] border bg-white p-6 md:p-8"
          style={{ borderColor: LINE }}
        >
          <div className="min-w-[260px] flex-1">
            <Kicker>WHY WE PUBLISH PRICES</Kicker>
            <h2 className="serif mb-0 mt-2 text-[24px] font-medium leading-tight tracking-[-0.02em] md:text-[28px]">
              Compliance software should not need a discovery call to reveal a number
            </h2>
          </div>
          <p className="m-0 min-w-[260px] flex-1 text-[14px] leading-relaxed" style={{ color: BODY }}>
            In Indian GRC, essentially every vendor hides pricing behind a demo; the only public entry
            price in the market is ₹2,600 a month, for a checklist product without AI extraction, a
            knowledge graph, or gap analysis. We would rather you know where you stand before we ever
            talk.
          </p>
        </section>

        {/* Comparison table */}
        <section className="flex flex-col gap-5">
          <div className="text-center">
            <Kicker>WHAT EACH TIER INCLUDES</Kicker>
            <h2 className="serif mb-0 mt-2.5 text-[28px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[36px]">
              Compare the tiers
            </h2>
          </div>
          <div className="overflow-x-auto rounded-[20px] border bg-white" style={{ borderColor: LINE }}>
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr className="border-b" style={{ borderColor: LINE }}>
                  <th className="px-5 py-4 text-[12px] font-semibold" style={{ color: MUTED }}>
                    Feature
                  </th>
                  {TIERS.map((t) => (
                    <th
                      key={t.name}
                      className="mono w-[120px] px-4 py-4 text-center text-[11px] font-semibold tracking-[.12em]"
                      style={{ color: t.highlight ? ACCENT : MUTED }}
                    >
                      {t.name.toUpperCase()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPARE.map((r, i) => (
                  <tr key={r.row} className={i > 0 ? "border-t" : ""} style={{ borderColor: "#F4F4F1" }}>
                    <td className="px-5 py-3 text-[13px]" style={{ color: "#3A3D44" }}>
                      {r.row}
                    </td>
                    {r.tiers.map((v, j) => (
                      <td
                        key={j}
                        className="px-4 py-3 text-center text-[13px]"
                        style={j === 1 ? { background: "rgba(75,64,196,.04)" } : undefined}
                      >
                        <CellValue v={v} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* FAQ */}
        <section className="mx-auto flex w-full max-w-[820px] flex-col gap-6">
          <div className="text-center">
            <Kicker>QUESTIONS BUYERS ACTUALLY ASK</Kicker>
            <h2 className="serif mb-0 mt-2.5 text-[28px] font-medium leading-[1.1] tracking-[-0.02em] md:text-[36px]">
              Frequently asked
            </h2>
          </div>
          <Faq items={FAQS} />
        </section>

        <TrustStrip
          items={[
            "Org-isolated by Postgres row-level security",
            "No training on your data",
            "Provider-switchable LLMs",
            "Cancel anytime",
          ]}
        />

        <CtaBand
          title="Start free, or start with a conversation"
          body="Sign up and see your obligations register today, or talk to us about Growth and Enterprise, procurement, and rollout."
          primary={{ label: "Start free", href: "/login" }}
          secondary={{ label: "Talk to us", href: "/contact?intent=sales" }}
        />
      </main>
    </MarketingShell>
  );
}
