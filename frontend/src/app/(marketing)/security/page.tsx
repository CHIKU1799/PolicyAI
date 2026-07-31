import type { Metadata } from "next";
import MarketingShell from "@/components/marketing/Shell";
import {
  ACCENT,
  BODY,
  CheckItem,
  CtaBand,
  FAINT,
  INK,
  Kicker,
  LINE,
  MUTED,
  PageHero,
} from "@/components/marketing/mkt2/ui";

export const metadata: Metadata = {
  title: "Security · PolicyAI",
  description:
    "How PolicyAI isolates and protects every firm's data: row-level security, private storage, org-keyed caches, and no training on customer data.",
};

/** Small stroke icon in a tinted tile. */
function IconTile({ path }: { path: React.ReactNode }) {
  return (
    <span
      className="flex h-10 w-10 flex-none items-center justify-center rounded-xl"
      style={{ background: "rgba(75,64,196,.1)", color: ACCENT }}
      aria-hidden
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {path}
      </svg>
    </span>
  );
}

const ICONS = {
  shield: <path d="M12 3l7 3v5c0 4.4-3 8.4-7 9.7C8 19.4 5 15.4 5 11V6l7-3z" />,
  key: (
    <>
      <circle cx="8" cy="15" r="4" />
      <path d="M11 12L20 3m-3 3l3 3" />
    </>
  ),
  folder: (
    <>
      <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" />
      <path d="M12 11v5m-2.5-2.5h5" />
    </>
  ),
  server: (
    <>
      <rect x="3" y="4" width="18" height="7" rx="2" />
      <rect x="3" y="13" width="18" height="7" rx="2" />
      <path d="M7 7.5h.01M7 16.5h.01" />
    </>
  ),
  chip: (
    <>
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </>
  ),
};

const SECTIONS: {
  id?: string;
  icon: React.ReactNode;
  kicker: string;
  title: string;
  body: string;
  bullets: string[];
}[] = [
  {
    id: "isolation",
    icon: ICONS.shield,
    kicker: "ORG ISOLATION",
    title: "Every firm is its own workspace",
    body: "Signing up provisions a fresh, isolated organization. Postgres row-level security runs with the caller's own token on every org-scoped table, so a session can only ever read its own firm's rows. Isolation is enforced at the database layer, not by UI hiding.",
    bullets: [
      "Row-level security on obligations, gaps, controls, policies, tasks and alerts",
      "The API derives your org from the verified token and ignores client claims",
      "The shared regulation graph is common by design; everything firm-specific is org-scoped",
    ],
  },
  {
    icon: ICONS.key,
    kicker: "AUTHENTICATION & ROLES",
    title: "Confirmed emails, invite-only teams",
    body: "Accounts are confirmed by email through Supabase Auth. Teammates join only by invitation: an invited email joins the inviting firm's workspace at signup instead of getting a new one. Access is role-based, and the last admin of a workspace can never be demoted.",
    bullets: [
      "Email confirmation before first login",
      "Admin-gated areas: document uploads and team management",
      "Last-admin guard prevents accidental lockout",
    ],
  },
  {
    icon: ICONS.folder,
    kicker: "DATA HANDLING",
    title: "Private storage, and no training on your data",
    body: "Your policy documents live in a private storage bucket with no public access; only server-side code holding the service role can read them. Nothing you upload is ever used to train AI models, and nothing derived from your data is visible to any other firm.",
    bullets: [
      "Documents in a private bucket, served through authenticated paths only",
      "Service-role credentials stay server-side; the browser holds only the public anon key",
      "No training on customer data, contractually and architecturally",
    ],
  },
  {
    icon: ICONS.server,
    kicker: "INFRASTRUCTURE",
    title: "Managed platforms, TLS everywhere",
    body: "PolicyAI runs on Sevalla with data on Supabase's managed Postgres. All traffic is encrypted in transit with TLS, data is encrypted at rest, and secrets live in environment configuration, never in code or the client bundle.",
    bullets: [
      "TLS in transit, encryption at rest on managed Postgres",
      "Secrets in env configuration, not in the repository",
      "Internal service endpoints guarded by a shared secret",
    ],
  },
  {
    icon: ICONS.chip,
    kicker: "LLM SAFETY",
    title: "Switchable providers, org-keyed caches",
    body: "The AI layer is provider-switchable in one command, from frontier models to open-weight models, and Enterprise deployments can run an open-weight model on your own infrastructure. Prompt and result caching never crosses firms: caches are keyed per organization.",
    bullets: [
      "Provider flexibility: frontier or open-weight models, your call",
      "On-prem open-weight option for Enterprise",
      "Cached extractions and answers are org-keyed; nothing leaks across workspaces",
    ],
  },
  {
    icon: ICONS.mail,
    kicker: "RESPONSIBLE DISCLOSURE",
    title: "Found something? Tell us directly",
    body: "If you believe you have found a vulnerability, write to us and include steps to reproduce. We acknowledge reports within one business day, keep you informed while we fix, and credit reporters who wish to be named.",
    bullets: [
      "security@policyai.com for vulnerability reports",
      "Acknowledgement within one business day",
      "Vendor security questionnaires answered within one business week",
    ],
  },
];

const ROADMAP = [
  "SOC 2 (roadmap)",
  "ISO 27001 (roadmap)",
  "SAML SSO & SCIM",
  "Granular RBAC & activity log",
  "India-region data residency",
];

export default function SecurityPage() {
  return (
    <MarketingShell>
      <main className="mx-auto flex max-w-[1304px] flex-col gap-16 px-5 pb-24 pt-12 md:gap-24 md:px-8 md:pt-16">
        <PageHero
          kicker="SECURITY"
          title="Built like your regulator is watching"
          lede="No badge theatre and no vague claims. This page describes exactly how your data is isolated and protected today, and what is still on the roadmap, in the language your vendor-risk review will use."
        />

        {/* Posture cards */}
        <section className="grid gap-4 md:grid-cols-2">
          {SECTIONS.map((s, i) => (
            <div
              key={s.title}
              id={s.id}
              className="anim-rise flex scroll-mt-24 flex-col gap-3.5 rounded-[20px] border bg-white p-6 md:p-7"
              style={{ borderColor: LINE, animationDelay: `${i * 0.05}s` }}
            >
              <div className="flex items-center gap-3.5">
                <IconTile path={s.icon} />
                <Kicker>{s.kicker}</Kicker>
              </div>
              <h2 className="m-0 text-[20px] font-bold leading-snug tracking-[-0.01em]" style={{ color: INK }}>
                {s.title}
              </h2>
              <p className="m-0 text-pretty text-[13.5px] leading-relaxed" style={{ color: BODY }}>
                {s.body}
              </p>
              <ul className="m-0 mt-auto flex list-none flex-col gap-2 border-t p-0 pt-3.5" style={{ borderColor: "#F4F4F1" }}>
                {s.bullets.map((b) => (
                  <CheckItem key={b}>{b}</CheckItem>
                ))}
              </ul>
            </div>
          ))}
        </section>

        {/* How isolation actually works */}
        <section
          className="grid gap-8 rounded-[20px] border bg-white p-6 md:grid-cols-2 md:p-8"
          style={{ borderColor: LINE }}
        >
          <div>
            <Kicker>UNDER THE HOOD</Kicker>
            <h2 className="serif mb-0 mt-2.5 text-[26px] font-medium leading-[1.15] tracking-[-0.02em] md:text-[32px]">
              What &ldquo;isolated&rdquo; means, concretely
            </h2>
            <p className="mb-0 mt-3.5 text-pretty text-[14px] leading-relaxed" style={{ color: BODY }}>
              A compliance buyer should not have to take tenancy on faith. These are the actual
              mechanics: the database policy runs with your token, and privileged operations never
              leave the server.
            </p>
          </div>
          <div className="flex flex-col gap-2.5">
            {[
              {
                code: "row level security: enabled",
                note: "Every org-scoped table filters by workspace membership at the database layer, evaluated with the caller's own token.",
              },
              {
                code: "org_id = token.org",
                note: "The API resolves your firm from your verified session on every request; a client-supplied org id is ignored.",
              },
              {
                code: "storage: private bucket",
                note: "Uploaded documents are readable only by server-side code holding the service role; there are no public URLs.",
              },
              {
                code: "llm_cache key: (org, prompt)",
                note: "Cached AI results are keyed per organization, so one firm's answers can never surface in another firm's session.",
              },
            ].map((r) => (
              <div key={r.code} className="rounded-[14px] border p-3.5" style={{ borderColor: "#F0F0EC", background: "#FCFCFB" }}>
                <span className="mono text-[11.5px] font-semibold" style={{ color: ACCENT }}>
                  {r.code}
                </span>
                <div className="mt-1 text-[12px] leading-relaxed" style={{ color: MUTED }}>
                  {r.note}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Roadmap */}
        <section id="roadmap" className="flex scroll-mt-24 flex-col items-center gap-5 text-center">
          <Kicker>ROADMAP, STATED PLAINLY</Kicker>
          <h2 className="serif m-0 max-w-[24ch] text-[26px] font-medium leading-[1.15] tracking-[-0.02em] md:text-[32px]">
            What we have not built yet
          </h2>
          <p className="m-0 max-w-[62ch] text-pretty text-[14.5px] leading-relaxed" style={{ color: BODY }}>
            We claim no certifications we do not hold. These items are planned, not shipped; if one of
            them is a hard requirement for your firm, tell us and we will sequence it with you.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {ROADMAP.map((r) => (
              <span
                key={r}
                className="rounded-full border bg-white px-3.5 py-1.5 text-[12.5px] font-semibold"
                style={{ borderColor: LINE, color: "#3A3D44" }}
              >
                {r}
              </span>
            ))}
          </div>
          <p className="m-0 text-[12.5px]" style={{ color: FAINT }}>
            Running a vendor assessment? We answer security questionnaires within one business week.
          </p>
        </section>

        <CtaBand
          title="Trust is earned in the details"
          body="Ask us anything about the architecture. We will walk your security team through the actual policies, not a badge wall."
          primary={{ label: "Talk to us", href: "/contact?intent=sales" }}
          secondary={{ label: "See pricing", href: "/pricing" }}
        />
      </main>
    </MarketingShell>
  );
}
