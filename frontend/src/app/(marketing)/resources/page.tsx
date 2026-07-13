import type { Metadata } from "next";
import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import { Chip, Cta, Hero } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "Resources — PolicyAI",
  description: "Blog, documentation, changelog and system status.",
};

const CHANGELOG = [
  ["Jul 2026", "Copilot drafts impact assessments; structured markdown answers with cited sources"],
  ["Jul 2026", "Per-firm workspaces: every signup gets an isolated organization"],
  ["Jul 2026", "Operator fault checks: crawler freshness, mapping backlog, embedding coverage"],
  ["Jul 2026", "Knowledge-graph explorer: search, hover focus, degree-sized nodes"],
  ["Jul 2026", "Control-failure alerts raised at the database layer; 12-week pass-rate trends"],
  ["Jun 2026", "Bitemporal timeline: ask what the rules were as of any date"],
  ["Jun 2026", "Deep archive backfill for RBI and SEBI, beyond the current listing page"],
];

export default function ResourcesPage() {
  return (
    <MarketingShell>
      <Hero
        eyebrow="RESOURCES"
        title={<>Learn the system</>}
        lede="What shipped, how it works, and where to read more."
      />

      <section className="px-5 pb-4">
        <div className="mx-auto grid max-w-5xl gap-4 md:grid-cols-2">
          <Link
            href="/blog/copilot-impact-assessments"
            className="rounded-2xl border bg-white p-6 no-underline transition-shadow hover:shadow-lg"
            style={{ borderColor: "#EAE9E5" }}
          >
            <Chip>BLOG</Chip>
            <h3
              className="mt-3 text-[22px] font-medium leading-snug"
              style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
            >
              The Copilot now drafts impact assessments
            </h3>
            <p className="mt-2 text-[13px] leading-relaxed" style={{ color: "#54565E" }}>
              Pick a regulation, get an analyst-grade first pass: applicability, severity, the
              requirements that bite hardest, and prioritized actions. Grounded in your firm&apos;s
              profile, ready for human review.
            </p>
            <span className="mt-3 inline-block text-[13px] font-semibold" style={{ color: "#1746D6" }}>
              Read the post →
            </span>
          </Link>

          <div id="docs" className="rounded-2xl border bg-white p-6" style={{ borderColor: "#EAE9E5" }}>
            <Chip tone="green">DOCUMENTATION</Chip>
            <h3
              className="mt-3 text-[22px] font-medium leading-snug"
              style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
            >
              Under the hood
            </h3>
            <ul className="mt-3 space-y-2 text-[13px]" style={{ color: "#3A3D44" }}>
              <li>• Architecture: crawl → extract → graph → map → act</li>
              <li>• Compliance mapping: how the relevance gate works</li>
              <li>• Deploying: Render worker, Vercel frontend, Supabase data</li>
              <li>• The bitemporal model: valid time vs system time</li>
            </ul>
            <p className="mt-3 text-[12px]" style={{ color: "#71757E" }}>
              Full docs ship with the repository (docs/ directory).
            </p>
          </div>
        </div>
      </section>

      <section id="changelog" className="scroll-mt-24 px-5 py-8">
        <div className="mx-auto max-w-5xl rounded-2xl border bg-white p-6" style={{ borderColor: "#EAE9E5" }}>
          <h3
            className="text-[22px] font-medium"
            style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
          >
            Changelog
          </h3>
          <ul className="mt-4">
            {CHANGELOG.map(([when, what]) => (
              <li key={String(what)} className="flex gap-4 border-t py-2.5" style={{ borderColor: "#F1F0EC" }}>
                <span className="w-20 flex-none font-mono text-[11px]" style={{ color: "#9A9DA4" }}>
                  {when}
                </span>
                <span className="text-[13px]" style={{ color: "#3A3D44" }}>
                  {what}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section id="status" className="scroll-mt-24 px-5 pb-4">
        <div className="mx-auto flex max-w-5xl items-center gap-4 rounded-2xl border bg-white p-6" style={{ borderColor: "#EAE9E5" }}>
          <span className="h-3 w-3 flex-none animate-pulse rounded-full" style={{ background: "#1F9D5B" }} />
          <div>
            <div className="text-[14px] font-semibold" style={{ color: "#15254E" }}>
              All systems monitored
            </div>
            <div className="text-[12.5px]" style={{ color: "#71757E" }}>
              Crawler freshness, ingestion throughput, mapping backlog and alert flow are checked
              continuously by the PolicyAI operations team.
            </div>
          </div>
        </div>
      </section>

      <Cta title="Want a deeper walkthrough?" body="Book a demo and we will drive the live platform on your segment's regulations." />
    </MarketingShell>
  );
}
