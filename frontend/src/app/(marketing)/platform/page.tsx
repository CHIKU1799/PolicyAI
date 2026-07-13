import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import { Chip, Cta, Hero, MockCard, Section } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "Platform — PolicyAI",
  description: "Five modules that turn regulatory change into action, end to end.",
};

export default function PlatformPage() {
  return (
    <MarketingShell>
      <Hero
        eyebrow="THE PLATFORM"
        title={
          <>
            One connected system,
            <br />
            end to end
          </>
        }
        lede="From the first regulatory signal to an audit-ready policy: five modules that work as one continuous workflow, on a shared knowledge graph."
      />

      <Section
        id="monitor"
        step="01 · Monitor"
        title="Horizon scanning"
        body="Continuously monitor RBI, SEBI, IRDAI and more, with deep archive backfill. Every update is summarised within hours and scored against your business, so your team reads a briefing, not a backlog."
        bullets={[
          "Real-time AI alerts with severity scoring",
          "Multi-regulator source coverage",
          "Filtered press feeds: regulatory actions only",
        ]}
      >
        <div className="flex flex-col gap-2">
          <MockCard>
            <div className="mb-1.5 flex items-center gap-2">
              <span className="font-mono text-[10px] font-extrabold" style={{ color: "#1E5EF6" }}>RBI</span>
              <Chip tone="red">High impact</Chip>
              <span className="ml-auto text-[9px]" style={{ color: "#1F9D5B" }}>● Live</span>
            </div>
            <div className="font-semibold" style={{ color: "#1A1C22" }}>
              Digital Lending Directions: disclosure obligations updated
            </div>
            <div className="mt-1 text-[11px]" style={{ color: "#71757E" }}>
              AI summary: 4 obligations affecting Microfinance
            </div>
          </MockCard>
          <MockCard>
            <div className="mb-1.5 flex items-center gap-2">
              <span className="font-mono text-[10px] font-extrabold" style={{ color: "#1E5EF6" }}>SEBI</span>
              <Chip tone="amber">Medium</Chip>
            </div>
            <div className="font-semibold" style={{ color: "#1A1C22" }}>
              Cybersecurity framework for regulated entities
            </div>
          </MockCard>
        </div>
      </Section>

      <Section
        id="structure"
        step="02 · Structure"
        title="Change becomes structured obligations"
        body="Each regulatory update becomes discrete, trackable obligations, automatically mapped to the right policies, owners, controls and products."
        bullets={[
          "AI extraction from any document",
          "Mapped to policy, owner, control, product",
          "Full traceability from rule to action",
        ]}
        flip
      >
        <MockCard>
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-[10px] font-bold" style={{ color: "#1746D6" }}>
              RBI DL Directions
            </span>
            <span className="text-[10px]" style={{ color: "#71757E" }}>4 obligations</span>
          </div>
          {[
            ["OBL-1044", "Offer key-fact statement before disbursal"],
            ["OBL-1045", "No fees on active repayment plans"],
            ["OBL-1046", "Evidence borrower-consent rationale"],
            ["OBL-1047", "Report concentration risk to board"],
          ].map(([id, t]) => (
            <div key={id} className="flex items-center gap-2 border-t py-1.5" style={{ borderColor: "#F1F0EC" }}>
              <Chip>{id}</Chip>
              <span className="text-[11.5px]" style={{ color: "#3A3D44" }}>{t}</span>
            </div>
          ))}
        </MockCard>
      </Section>

      <Section
        id="assess"
        step="03 · Assess"
        title="Gap analysis"
        body="Compare your policies, processes and controls against emerging requirements. See coverage and severity at a glance, and close gaps before they become findings, with the exact policy passage as citable evidence."
        bullets={[
          "Coverage classification per requirement",
          "Severity-based triage",
          "AI-suggested remediation steps",
        ]}
      >
        <MockCard>
          <div className="mb-2 text-[11px] font-semibold" style={{ color: "#1A1C22" }}>
            Coverage vs. requirements
          </div>
          {[
            ["Audit trail for forbearance", 28, "red"],
            ["Board concentration reporting", 76, "amber"],
            ["Fairness testing — credit", 45, "amber"],
            ["Enhanced CDD triggers", 85, "green"],
          ].map(([label, pct, tone]) => (
            <div key={String(label)} className="mb-2">
              <div className="mb-1 flex justify-between text-[10.5px]" style={{ color: "#54565E" }}>
                <span>{label}</span>
                <span>{pct}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full" style={{ background: "#F0F0EC" }}>
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${pct}%`,
                    background: tone === "green" ? "#1F9D5B" : tone === "amber" ? "#E0683C" : "#C0392B",
                  }}
                />
              </div>
            </div>
          ))}
        </MockCard>
      </Section>

      <Section
        id="test"
        step="04 · Test"
        title="Controls testing & monitoring"
        body="Real-time control effectiveness with continuous testing and trend monitoring. Know the moment a control starts to drift, not at the next audit."
        bullets={[
          "Test history with pass-rate trends",
          "12-week effectiveness chart",
          "Alerts the moment a control fails",
        ]}
        flip
      >
        <MockCard>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold" style={{ color: "#1A1C22" }}>Control effectiveness</span>
            <Chip tone="green">+ Live</Chip>
          </div>
          {[
            ["Forbearance eligibility", "96% effective", "green"],
            ["Late-fee suppression", "99% effective", "green"],
            ["Fairness monitor", "58% effective", "red"],
          ].map(([name, val, tone]) => (
            <div key={String(name)} className="flex items-center justify-between border-t py-1.5" style={{ borderColor: "#F1F0EC" }}>
              <span className="text-[11.5px]" style={{ color: "#3A3D44" }}>{name}</span>
              <Chip tone={tone as "green" | "red"}>{val}</Chip>
            </div>
          ))}
        </MockCard>
      </Section>

      <Section
        id="govern"
        step="05 · Govern"
        title="Policy governance"
        body="A central policy library with full versioning, review and approval workflows, and audit-ready traceability across the entire lifecycle. Every change, every approval, evidenced and searchable."
        bullets={[
          "Central library with version control",
          "Review and approval trail",
          "Exportable audit trail (CSV)",
        ]}
      >
        <MockCard>
          <div className="mb-2 text-[11px] font-semibold" style={{ color: "#1A1C22" }}>
            Version history · POL-04
          </div>
          {[
            ["v4.3", "Digital Lending disclosure obligations", "CURRENT"],
            ["v4.2", "Annual review, §2 clarifications", ""],
            ["v4.1", "Added debt-advice signposting", ""],
          ].map(([v, note, tag]) => (
            <div key={String(v)} className="flex items-center gap-2 border-t py-1.5" style={{ borderColor: "#F1F0EC" }}>
              <Chip>{v}</Chip>
              <span className="text-[11.5px]" style={{ color: "#3A3D44" }}>{note}</span>
              {tag && <Chip tone="green">{tag}</Chip>}
            </div>
          ))}
        </MockCard>
      </Section>

      <Section
        id="graph"
        step="Foundation"
        title="The regulatory knowledge graph"
        body="Indian regulation is relational: circulars amend master directions, apply to entity classes, and derive from parent acts. PolicyAI preserves those relationships in a graph of 2,800+ nodes, so applicability, supersession and deadlines are queryable instead of buried in PDFs."
        bullets={[
          "780+ regulations, 7,000+ extracted requirements",
          "Amends / supersedes / applies-to edges",
          "Explorable in-app with search and drill-down",
        ]}
        flip
      >
        <div className="flex h-full items-center justify-center">
          <svg viewBox="0 0 260 160" className="w-full max-w-[280px]">
            <g stroke="#CBD5E1" strokeWidth="1">
              {[
                [130, 80, 40, 30],
                [130, 80, 220, 30],
                [130, 80, 30, 120],
                [130, 80, 200, 130],
                [130, 80, 130, 20],
              ].map(([x1, y1, x2, y2], i) => (
                <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />
              ))}
            </g>
            <circle cx="130" cy="80" r="16" fill="#059669" />
            <circle cx="40" cy="30" r="9" fill="#1d4ed8" />
            <circle cx="220" cy="30" r="9" fill="#1d4ed8" />
            <circle cx="30" cy="120" r="9" fill="#d97706" />
            <circle cx="200" cy="130" r="9" fill="#1d4ed8" />
            <circle cx="130" cy="20" r="9" fill="#4b40c4" />
          </svg>
        </div>
      </Section>

      <Cta
        title="See your compliance posture in one place"
        body="Join the compliance teams who turn regulatory change into action, without the spreadsheets."
      />
    </MarketingShell>
  );
}
