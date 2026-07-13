import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import { Cta, Hero, Section } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "Security — PolicyAI",
  description: "How PolicyAI protects and isolates every firm's data.",
};

export default function SecurityPage() {
  return (
    <MarketingShell>
      <Hero
        eyebrow="SECURITY"
        title={
          <>
            Secure by design,
            <br />
            honest by default
          </>
        }
        lede="No badge theatre. This page describes exactly how your data is protected today, and what is still on the roadmap."
      />

      <Section
        id="isolation"
        step="Tenant isolation"
        title="Every firm is its own island"
        body="Sign-up provisions a fresh, isolated organization. Row-level security in Postgres enforces that a firm's browser session can only ever read its own rows; the API independently derives your organization from your verified session token and ignores anything the client claims."
        bullets={[
          "Postgres row-level security on every org-scoped table",
          "API org-scoping from the verified token, spoof-tested",
          "Platform operators are separated by role, not by trust",
        ]}
      >
        <div className="space-y-2 text-[12px]" style={{ color: "#3A3D44" }}>
          <div className="rounded-lg border bg-white p-3" style={{ borderColor: "#EAE9E5" }}>
            <span className="font-mono text-[11px]" style={{ color: "#1746D6" }}>
              org_id = token.org
            </span>
            <div className="mt-1 text-[11px]" style={{ color: "#71757E" }}>
              The worker resolves your firm from Supabase Auth on every request. A client-supplied
              org id is ignored unless you are a platform operator.
            </div>
          </div>
          <div className="rounded-lg border bg-white p-3" style={{ borderColor: "#EAE9E5" }}>
            <span className="font-mono text-[11px]" style={{ color: "#1746D6" }}>
              row level security: enabled
            </span>
            <div className="mt-1 text-[11px]" style={{ color: "#71757E" }}>
              Obligations, gaps, controls, policies, documents, alerts: all filtered by membership
              at the database layer.
            </div>
          </div>
        </div>
      </Section>

      <Section
        step="Data protection"
        title="Encryption and least privilege"
        body="Data is encrypted in transit (TLS) and at rest on Supabase's managed Postgres. Secrets never ship to the browser; the frontend holds only the public anon key, and privileged operations run server-side behind a shared-secret internal API."
        bullets={[
          "TLS in transit, AES-256 at rest (managed Postgres)",
          "Anon key in the browser, service credentials server-side only",
          "Internal endpoints guarded by a shared secret",
        ]}
        flip
      >
        <div className="flex h-full items-center justify-center">
          <div className="rounded-xl border bg-white px-6 py-5 text-center" style={{ borderColor: "#EAE9E5" }}>
            <div className="text-[28px]">🔒</div>
            <div className="mt-1 text-[12px] font-semibold" style={{ color: "#15254E" }}>
              Encrypted at rest & in transit
            </div>
            <div className="text-[11px]" style={{ color: "#71757E" }}>
              Supabase managed Postgres
            </div>
          </div>
        </div>
      </Section>

      <Section
        step="Operations"
        title="Operator oversight with fault checks"
        body="The PolicyAI operations team monitors the machine that feeds every firm: crawler freshness, scan failures, ingestion throughput, mapping backlog and alert flow, from a console individual firms never see."
        bullets={[
          "Continuous system health checks",
          "Control failures raise alerts at the database layer",
          "Cross-firm visibility restricted to seeded platform admins",
        ]}
      >
        <div className="space-y-1.5 text-[11.5px]">
          {[
            ["ok", "Scan runs (24h): no failures"],
            ["ok", "Embeddings: all documents embedded"],
            ["warn", "Mapping backlog: monitored"],
            ["ok", "Alerts: flowing, 0 control failures"],
          ].map(([tone, label]) => (
            <div key={String(label)} className="flex items-center gap-2 rounded-lg border bg-white px-3 py-2" style={{ borderColor: "#EAE9E5" }}>
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: tone === "ok" ? "#1F9D5B" : "#E0A63C" }}
              />
              <span style={{ color: "#3A3D44" }}>{label}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="roadmap"
        step="Roadmap"
        title="What we have not built yet"
        body="We would rather tell you plainly. These are planned, not shipped; if any of them is a hard requirement for your firm, talk to us and we will sequence accordingly."
        bullets={[
          "SAML SSO and SCIM provisioning",
          "India-region data residency",
          "Granular RBAC and full activity logging",
          "Third-party certifications (SOC 2, ISO 27001)",
        ]}
        flip
      >
        <div className="flex h-full items-center justify-center text-center">
          <div>
            <div className="text-[13px] font-semibold" style={{ color: "#15254E" }}>
              Security questionnaire?
            </div>
            <div className="mt-1 max-w-[220px] text-[12px]" style={{ color: "#71757E" }}>
              We answer vendor-risk questionnaires within one business week.
            </div>
            <a
              href="/contact?intent=sales"
              className="mt-3 inline-block rounded-lg px-4 py-2 text-[12.5px] font-semibold text-white no-underline"
              style={{ background: "linear-gradient(135deg,#2E6BF7,#1746D6)" }}
            >
              Contact us
            </a>
          </div>
        </div>
      </Section>

      <Cta title="Trust is earned in the details" body="Ask us anything about the architecture. We will show you the actual policies, not a badge wall." />
    </MarketingShell>
  );
}
