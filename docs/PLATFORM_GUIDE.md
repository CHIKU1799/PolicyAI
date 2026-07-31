# PolicyAI Platform Guide

The one document to hand to a new team member, a customer, or a demo audience.
What the platform does, how a company actually uses it, who can access what,
and every switch that has to be set for a deployment to work.

---

## 1. What PolicyAI is

PolicyAI watches Indian financial regulators around the clock, turns every
circular into structured obligations on a live knowledge graph, maps those
obligations against a firm's own policy documents, and tracks the resulting
gaps, controls and tasks until they are closed. One sentence for a demo:
"Every circular, mapped to the obligation it creates, checked against your
own policies."

Sources monitored today: RBI (notifications + press releases), SEBI
(circulars + master circulars), IRDAI, MCA, PIB, CERT-In, PFRDA, IFSCA,
FIU-IND. NPCI and DGFT are wired and activate once OCR is enabled. The
crawler runs every 6 hours; per-source cadence is enforced internally.

## 2. Feature tour (what to show, in demo order)

| Feature | Where | What it does |
|---|---|---|
| Compliance Dashboard | /dashboard | Posture score, KPI cards with real deltas, executive briefing, Horizon feed of latest regulatory activity with per-regulator chips, upcoming deadlines, gaps by severity |
| Posture improvement | /dashboard (mid-page) | Are we better than before: coverage delta vs the previous policy upload, gaps resolved, 12-week resolution trend, per-document comparison |
| Horizon scanning | Dashboard "Scan now" | On-demand crawl of all enabled sources; new items appear as alerts in minutes |
| Obligations register | /obligations | Every obligation extracted for your entity classes, filterable by severity, exportable |
| Knowledge Graph | /graph | The regulatory web itself: regulations, amendments, supersessions, entity classes, topics, deadlines; search, hop depth, node inspection |
| Gap analysis | /gaps | Your uploaded policies diffed against applicable requirements, 4-state coverage per requirement, remediation plans, severity triage |
| Controls testing | /controls | Define controls for obligations, record pass/partial/fail tests, effectiveness rollup, failure alerts; includes a how-to guide panel |
| Policies | /policies | The firm's policy library with owners and versions |
| Tasks | /tasks | Owned, dated remediation work generated from gaps and alerts |
| Knowledge Base (admin only) | /knowledge-base | Upload company policy documents; drives profile derivation and gap mapping |
| PolicyAI Copilot | /ask | Grounded chat over your org's live compliance state plus the regulation corpus, with citations; falls back through worker, then a serverless free-model chain |
| Team (admin only) | /team | Invite teammates by email, grant or revoke admin, cancel pending invites |
| Platform admin console | /admin | Cross-org KPIs and per-company table; platform admins only |
| Onboarding tour | auto on first login, replay via the ? icon | 10-step animated spotlight tour of everything above |

## 3. How a company uses it (the lifecycle)

Day 1:
1. Sign up with company name at /login. A fresh, isolated workspace (org) is
   provisioned automatically; the signer-up becomes its admin.
2. The onboarding tour walks them through the features.
3. Admin uploads the firm's policy documents in Knowledge Base (KYC policy,
   fair practices code, IT policy, whatever exists). PolicyAI derives the
   company profile (entity classes such as NBFC-MFI, payment aggregator).
4. Obligation mapping runs: applicable obligations appear in the register,
   gaps appear where the uploaded policies fall short, each with the exact
   regulation passage as evidence.
5. Admin invites the team from /team (compliance officers as members,
   a co-admin as admin).

Ongoing, weekly rhythm:
- The crawler ingests new circulars every 6 hours; Horizon alerts flag what
  is new and how severe.
- The team works the gap list: assign remediation, attach it to tasks, close.
- Controls are tested on their cadence; failures raise alerts instantly.
- The Copilot answers "what changed for us this month", "which of our
  policies fail the new digital lending rules", with citations.
- After the next policy revision is uploaded, Posture improvement shows the
  delta: coverage up, gaps closed.

## 4. Access model (who sees what)

Three levels:

1. **Org member**: everything in their own org except Knowledge Base and
   Team. Cannot see other orgs. Data isolation is enforced by Postgres RLS
   with the caller's Supabase token, not just UI hiding.
2. **Org admin**: everything a member sees, plus Knowledge Base (uploads)
   and Team (invite, promote, demote; the last admin can never be demoted).
   The signup founder is the first admin. Invited emails join the inviting
   org at signup instead of getting a new org.
3. **Platform admin** (you, the operator): cross-org visibility, /admin
   console. Seeded with `make seed-admin EMAIL=...`; platform admins skip
   org provisioning at signup.

Unauthenticated visitors see the marketing site and, if they hit the app,
read-only demo-org data. The shared regulation graph (nodes/edges) is
common to all orgs by design; everything firm-specific is org-scoped.

## 5. Deployment configuration (Sevalla), the complete checklist

Two apps built from GitHub `main` with the existing Dockerfiles. See
DEPLOY.md for the long-form version; this is the everything-set checklist.

**App: policyai-api** (docker/api.Dockerfile, context `.`)
- Env (runtime): `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
  `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_KB_BUCKET=company-documents`,
  `FRONTEND_ORIGINS=https://policyai.com,https://www.policyai.com`
  (the built-in regex already allows *.sevalla.app and policyai.com, the
  explicit list is belt-and-braces), `INTERNAL_API_SECRET=<random>`,
  `LLM_PROVIDER` + the active provider key (see 7), `EMBEDDING_PROVIDER`
  (`local` needs 2 GB RAM + persistent storage at /data; `cohere`/`hf`
  avoid both), `RERANK_PROVIDER` + `COHERE_API_KEY`, `OCR_ENABLED=1`.
- Processes: web (default CMD, binds injected PORT, health check /ready),
  cron `uv run --no-sync python -m policyai_scrapers.runner` at `0 */6 * * *`,
  cron `uv run --no-sync python -m policyai_extraction.digest` at `30 3 * * *`.
- Migrations for future releases: Web Terminal, then
  `cd packages/graph && uv run --no-sync alembic upgrade head`.

**App: policyai-web** (docker/web.Dockerfile, context `.`)
- Env (BUILD-time, baked into the bundle; changing them needs a rebuild):
  `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
  `NEXT_PUBLIC_SUPABASE_KB_BUCKET`, `NEXT_PUBLIC_API_URL=<api app URL>`.
- Env (runtime, optional): the LLM keys for the backup Copilot
  (`GROQ_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`,
  `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, any subset).
- Domain: policyai.com attached here.

**Supabase (dashboard, one-time)**
- Auth URL configuration: Site URL `https://policyai.com`; redirect URLs
  `https://policyai.com/auth/callback` (+ www variant, + the sevalla.app
  fallback URL's /auth/callback, + `http://localhost:3001/auth/callback`).
- Custom SMTP (e.g. Resend) under Auth -> Emails: the built-in sender is
  ~2 emails/hour and resends invalidate older links.
- All schema migrations (alembic 0015 + supabase SQL 0014) are applied.

**Turn on auto-deploy on push for both apps.** Stale deploys have bitten
this project twice.

## 6. Cost and caching (what keeps the bill down)

- Anthropic prompt caching: system prompts and tool schemas are marked
  cacheable; bulk runs pay ~10% for the repeated prefix. Run summaries
  print cached tokens and dollars saved.
- Persistent result cache (`llm_cache` table): identical extraction and
  mapping calls replay free; killed backfills lose nothing. Disable with
  `LLM_RESULT_CACHE=0`.
- Endpoint TTL cache: /insights per org (90 s), shared graph subgraph
  (300 s).
- Crawler dedup: content-hash prevents re-extracting anything unchanged.

## 7. LLM providers (open source and paid, switchable in one command)

`make llm-status` shows the active provider. Switching edits .env; restart
the worker after.

| Command | Provider | Model | Use for |
|---|---|---|---|
| `make llm-claude` | Anthropic (paid) | sonnet extraction, opus mapping | Best quality: Copilot, mapping |
| `make llm-glm` | Z.ai (cheap paid) | GLM-5.2 (open weights, MIT) | Bulk extraction without daily caps |
| `make llm-kimi` | Moonshot (cheap paid) | Kimi K2.5 (open weights) | Same, cheapest strong option |
| `make llm-cerebras` | Cerebras (free tier) | gpt-oss-120b | Free bulk, ~1M tokens/day |
| `make llm-groq` | Groq (free tier) | llama-3.3-70b | Light interactive use only |
| `make llm-gemini` / `llm-mistral` / `llm-openrouter` | free tiers | various | Fallbacks |

Other open-source components already in the stack: bge-m3 local embeddings
(no per-call cost), RapidOCR for scanned regulator PDFs, Playwright for
walled-site crawling, pgvector for retrieval.

## 8. Known limits (say these before a prospect finds them)

- NPCI and DGFT publish scanned PDFs; they activate with OCR enabled.
- CBDT, CBIC and eGazette resist automated collection (WAF/portal issues);
  their content arrives indirectly via PIB and gazette coverage elsewhere.
- Exchange/depository circulars (NSE/BSE/NSDL/CDSL) are not yet crawled.
- No compliance calendar, board report pack, or maker-checker workflow yet;
  these are the top roadmap items in docs/competitive_alignment_2026-07.md.
- Email invites do not send an email yet; the invite activates when the
  invitee signs up with that address.
