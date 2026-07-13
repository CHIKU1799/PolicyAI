import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import { Cta, Hero } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "Pricing — PolicyAI",
  description: "Simple early-access pricing for Indian BFSI compliance teams.",
};

const TIERS = [
  {
    name: "Pilot",
    price: "Free",
    period: "during early access",
    highlight: false,
    blurb: "For one compliance team proving the workflow.",
    features: [
      "1 firm workspace, isolated by design",
      "Full regulatory corpus (RBI, SEBI, IRDAI)",
      "Obligation mapping for your profile",
      "Gap analysis against your policies",
      "PolicyAI Copilot with citations",
    ],
    cta: "Start free",
  },
  {
    name: "Growth",
    price: "₹49k",
    period: "per month, billed annually",
    highlight: true,
    blurb: "For teams running compliance on PolicyAI daily.",
    features: [
      "Everything in Pilot",
      "Impact-assessment drafting",
      "Controls testing with failure alerts",
      "Policy governance with audit export",
      "Daily digest and email alerts",
      "Priority support",
    ],
    cta: "Book a demo",
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "annual agreement",
    highlight: false,
    blurb: "For groups, multiple entities, and bespoke controls.",
    features: [
      "Multiple workspaces under one group",
      "Operator-grade reporting",
      "Security questionnaire support",
      "Roadmap input: SSO/SCIM, residency",
      "Dedicated onboarding",
    ],
    cta: "Talk to sales",
  },
];

export default function PricingPage() {
  return (
    <MarketingShell>
      <Hero
        eyebrow="PRICING"
        title={<>Priced for teams, not seats</>}
        lede="Early-access pricing while we onboard design partners. Every tier includes the full regulatory corpus; you never pay per regulation."
      />
      <section className="px-5 pb-6">
        <div className="mx-auto grid max-w-5xl gap-4 md:grid-cols-3">
          {TIERS.map((t) => (
            <div
              key={t.name}
              className="relative rounded-2xl border bg-white p-6"
              style={{
                borderColor: t.highlight ? "#1E5EF6" : "#EAE9E5",
                boxShadow: t.highlight ? "0 16px 40px -14px rgba(23,70,214,.35)" : undefined,
              }}
            >
              {t.highlight && (
                <span
                  className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-white"
                  style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
                >
                  Most popular
                </span>
              )}
              <div className="text-[13px] font-bold uppercase tracking-wide" style={{ color: "#71757E" }}>
                {t.name}
              </div>
              <div
                className="mt-2 text-[38px] font-medium"
                style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
              >
                {t.price}
              </div>
              <div className="text-[12px]" style={{ color: "#9A9DA4" }}>
                {t.period}
              </div>
              <p className="mt-3 text-[13px]" style={{ color: "#54565E" }}>
                {t.blurb}
              </p>
              <ul className="mt-4 space-y-2">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-[12.5px]" style={{ color: "#3A3D44" }}>
                    <span
                      className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded-full text-[9px] font-bold text-white"
                      style={{ background: "#1F9D5B" }}
                    >
                      ✓
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href="/login"
                className="mt-6 block rounded-xl py-2.5 text-center text-[13.5px] font-semibold no-underline"
                style={
                  t.highlight
                    ? { background: "linear-gradient(135deg,#2E6BF7,#1746D6)", color: "#fff" }
                    : { border: "1px solid #E2E1DC", color: "#3A3D44" }
                }
              >
                {t.cta}
              </a>
            </div>
          ))}
        </div>
        <p className="mx-auto mt-6 max-w-xl text-center text-[12px]" style={{ color: "#9A9DA4" }}>
          Early-access numbers, subject to change as we exit design-partner phase. No card required
          for Pilot; cancel anytime.
        </p>
      </section>
      <Cta title="Not sure which tier?" body="Start on Pilot today; upgrading later keeps every obligation, gap and audit trail intact." />
    </MarketingShell>
  );
}
