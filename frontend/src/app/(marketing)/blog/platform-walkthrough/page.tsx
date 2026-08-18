import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import MarketingShell from "@/components/marketing/Shell";
import { Chip, Cta } from "@/components/marketing/blocks";

export const metadata: Metadata = {
  title: "From circular to audit-ready: the complete PolicyAI walkthrough · PolicyAI Blog",
  description:
    "Every step of the platform, in the order a compliance team actually uses it: sign up, watch the regulators, extract obligations, close gaps, test controls, and prove it all, with real screenshots.",
};

function P({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-4 text-[15px] leading-[1.75]" style={{ color: "#3A3D44" }}>
      {children}
    </p>
  );
}

function H2({ step, children }: { step?: string; children: React.ReactNode }) {
  return (
    <h2
      className="mb-3 mt-12 text-[26px] font-medium leading-snug"
      style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
    >
      {step && (
        <span className="mono mr-3 align-middle text-[11px] font-bold tracking-[.18em]" style={{ color: "#1E5EF6" }}>
          {step}
        </span>
      )}
      {children}
    </h2>
  );
}

function Shot({ src, alt, caption }: { src: string; alt: string; caption: string }) {
  return (
    <figure className="my-6">
      <div
        className="overflow-hidden rounded-[14px] border shadow-[0_18px_40px_-22px_rgba(17,18,27,.35)]"
        style={{ borderColor: "#E4E2DC" }}
      >
        <Image src={src} alt={alt} width={1440} height={900} className="h-auto w-full" />
      </div>
      <figcaption className="mt-2 text-center text-[12.5px]" style={{ color: "#8A8D95" }}>
        {caption}
      </figcaption>
    </figure>
  );
}

export default function WalkthroughPost() {
  return (
    <MarketingShell>
      <article className="px-5 pb-6 pt-12">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-3 flex items-center justify-center gap-2 text-[12px]" style={{ color: "#71757E" }}>
            <Chip>GUIDE</Chip>
            <span>August 2026</span>
            <span>·</span>
            <span>10 min read</span>
          </div>
          <h1
            className="text-[40px] font-medium leading-[1.1] tracking-tight md:text-[52px]"
            style={{ fontFamily: "var(--font-serif), serif", color: "#15254E" }}
          >
            From circular to audit-ready:
            <br />
            the complete <em style={{ color: "#1E5EF6" }}>walkthrough</em>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-[15px] leading-relaxed" style={{ color: "#54565E" }}>
            Every screen of PolicyAI, in the order a compliance team actually uses it. Real
            screenshots from a live workspace, not mockups.
          </p>
        </div>

        <div className="mx-auto max-w-2xl pt-8">
          <H2 step="STEP 1">Create your workspace</H2>
          <P>
            Sign up with your work email and company name; your workspace is provisioned instantly
            and you land in the app signed in. No confirmation-email dance, no sales call. If a
            teammate invited you, you join their firm&apos;s workspace automatically instead.
          </P>
          <Shot
            src="/blog/walkthrough/01-signup.jpg"
            alt="PolicyAI signup form"
            caption="Company name, email, password. The workspace exists before you finish reading this caption."
          />

          <H2 step="STEP 2">Read the room in one glance</H2>
          <P>
            The dashboard opens on your compliance posture: a single score built from control
            effectiveness, obligation coverage and open gaps, an executive briefing in plain
            sentences, and the priorities that need attention first. Everything on this screen
            clicks through to the page where you act on it.
          </P>
          <Shot
            src="/blog/walkthrough/02-dashboard.jpg"
            alt="PolicyAI compliance dashboard"
            caption="Posture score, executive briefing, and honest KPIs, computed from your live data."
          />

          <H2 step="STEP 3">Watch the horizon without watching it</H2>
          <P>
            PolicyAI&apos;s crawlers read RBI, SEBI, IRDAI, MCA, PFRDA, IFSCA, CERT-In, FIU-IND and
            more around the clock. Each new circular is scored against your business and lands in
            the Horizon feed as an alert, usually within minutes of publication. You can also
            trigger a scan on demand.
          </P>
          <Shot
            src="/blog/walkthrough/03-horizon-feed.jpg"
            alt="Horizon scanning feed of regulator alerts"
            caption="The regulators publish; the feed fills itself. Severity is scored against your profile, not generically."
          />

          <H2 step="STEP 4">Teach it your business</H2>
          <P>
            Upload your internal policies, registrations and licenses to the Knowledge Base.
            PolicyAI reads them to derive your company profile, which is what makes every alert,
            gap and answer specific to your firm rather than to a generic NBFC.
          </P>
          <Shot
            src="/blog/walkthrough/04-knowledge-base.jpg"
            alt="Knowledge Base document library"
            caption="Your documents stay org-isolated. The AI reads them so gap analysis can cite your own policy text."
          />

          <H2 step="STEP 5">Know exactly what binds you</H2>
          <P>
            Each regulation that applies to you becomes structured obligations: what is required,
            how severe it is, the exact citation, the penalty exposure, and what evidence an
            auditor would ask for. This is the register everything else hangs off.
          </P>
          <Shot
            src="/blog/walkthrough/05-obligations.jpg"
            alt="Obligations register"
            caption="Filter by severity, export the register, or open any obligation to see its controls, policies and tasks."
          />

          <H2 step="STEP 6">Run the whole flow from one page</H2>
          <P>
            The Workflow page shows the entire journey as a live pipeline: monitor, structure,
            assess, act, prove, govern. Below it, the allocation queue surfaces unassigned and
            overdue work first, and you assign every task an owner and a due date without leaving
            the page. The workload panel keeps the split across your team visible.
          </P>
          <Shot
            src="/blog/walkthrough/06-workflow.jpg"
            alt="Workflow pipeline and task allocation"
            caption="Six stages with live counts, then the queue: who does what, by when."
          />

          <H2 step="STEP 7">See what&apos;s missing before an auditor does</H2>
          <P>
            Gap analysis compares every requirement against your own policy documents and
            classifies the coverage: covered, partial, missing, or conflicting. Each card cites
            the exact policy passage (or its absence), and the board moves through open,
            remediating, accepted and closed.
          </P>
          <Shot
            src="/blog/walkthrough/07-gaps.jpg"
            alt="Gap analysis board"
            caption="Requirement coverage up top; below it, every gap with its severity and remediation state."
          />

          <H2 step="STEP 8">Prove your controls actually work</H2>
          <P>
            A control is the check that satisfies an obligation: a quarterly KYC file audit, a
            maker-checker gate before payouts. Define them here, link them to the obligations they
            satisfy, and record test results on schedule.
          </P>
          <Shot
            src="/blog/walkthrough/08-controls.jpg"
            alt="Controls testing register"
            caption="Every control with its type, owner, test frequency, effectiveness and latest result."
          />
          <P>
            Don&apos;t know what controls you need? Tick the obligations and press Suggest with AI:
            the platform drafts audit-grade controls, each with the sample checked, the cadence,
            and the evidence produced. You review, pick one, set an owner, and create it.
          </P>
          <Shot
            src="/blog/walkthrough/09-controls-ai.jpg"
            alt="AI-suggested controls for selected obligations"
            caption="Drafted from the obligation text and your existing register, so suggestions extend it rather than duplicate it."
          />
          <P>
            Recording a test takes one row: pass, partial or fail, with notes and evidence. A pass
            updates effectiveness instantly; a fail flips the control to ineffective and raises an
            alert on the dashboard automatically, before an auditor finds it for you.
          </P>
          <Shot
            src="/blog/walkthrough/10-record-test.jpg"
            alt="Recording a control test result inline"
            caption="Result, notes, evidence. Failures escalate themselves."
          />

          <H2 step="STEP 9">Keep policies governed, not scattered</H2>
          <P>
            The policy library holds your internal documents with versioning, review and approval
            workflows, and an exportable audit trail, so &ldquo;which version was in force in
            March?&rdquo; has an answer.
          </P>
          <Shot
            src="/blog/walkthrough/11-policies.jpg"
            alt="Policy library"
            caption="Versioned, owned, and traceable to the obligations each policy addresses."
          />

          <H2 step="STEP 10">Track the work like work</H2>
          <P>
            Every obligation generates concrete tasks with suggested owners and deadlines. The
            board view moves them through to-do, in progress, blocked and done; the Workflow page
            handles bulk allocation when the list is long.
          </P>
          <Shot
            src="/blog/walkthrough/12-tasks.jpg"
            alt="Task board"
            caption="Compliance as a to-do list with citations, not a 40-page PDF."
          />

          <H2 step="STEP 11">Ask anything, get a cited answer</H2>
          <P>
            The Copilot answers questions across the regulation corpus and your own data together:
            &ldquo;which gaps are critical?&rdquo;, &ldquo;what does the KYC master direction
            require?&rdquo;, &ldquo;how many tasks are overdue?&rdquo;. Every claim is grounded in
            a tool call and cited back to the source, and it refuses to guess when the data
            isn&apos;t there.
          </P>
          <Shot
            src="/blog/walkthrough/13-copilot.jpg"
            alt="Ask PolicyAI copilot with a cited answer"
            caption="Answers lead with the bottom line and carry their citations with them."
          />

          <H2 step="STEP 12">Bring the team</H2>
          <P>
            Invite teammates from the Team page; they join your org with the right role and appear
            as assignees everywhere immediately. Admins manage roles and pending invites from the
            same screen.
          </P>
          <Shot
            src="/blog/walkthrough/14-team.jpg"
            alt="Team management page"
            caption="Invite by email. Members land in your workspace, admins keep control."
          />

          <H2>The loop, closed</H2>
          <P>
            That&apos;s the whole system: a regulator publishes, PolicyAI reads it, decides whether
            it binds you, drafts the obligation, opens the gap, assigns the owner, and tracks the
            control until there&apos;s evidence on file. Your team walks in each morning to a
            prioritized list with citations, and walks into each audit with the proof already
            attached.
          </P>
          <p className="mt-6 text-[14px]">
            <Link href="/login" className="font-semibold no-underline" style={{ color: "#1746D6" }}>
              Start your workspace, it takes a minute →
            </Link>
          </p>
        </div>
      </article>

      <Cta
        title="See it on your own regulations"
        body="Sign up, upload one policy, and watch the gaps surface themselves."
      />
    </MarketingShell>
  );
}
