# PolicyAI Competitive Alignment Report: Indian RegTech

Date: 2026-07-29. Method: web research on vendor sites, brochures, review sites (Capterra, SoftwareSuggest, SoftwareFinder, G2), Tracxn, press coverage, plus an audit of the current PolicyAI codebase (`main`, see `docs/FEATURE_ALIGNMENT.md`). No em-dashes are used anywhere in this document by rule.

PolicyAI baseline used for comparison: crawlers for RBI, SEBI, IRDAI, MCA, PIB, PFRDA, IFSCA, NPCI, FIU-IND, CERT-In, CBIC, CBDT, DGFT, eGazette; knowledge graph with AMENDS / SUPERSEDES / APPLIES_TO / DERIVED_FROM edges; 6,900+ extracted requirements; obligation-to-org-profile mapping with severity and citations; 4-state gap analysis with remediation plans and a coverage % rollup; task board; controls + control tests (manual records); real-time in-app alerts with LLM severity; grounded Copilot with citations; force-graph explorer; multi-tenant orgs with a platform admin console. Known soft spots from the internal audit: only a subset of monitoring sources enabled, no compliance calendar, no board pack, no evidence repository, no maker-checker or escalation chains, no granular RBAC or activity log, no exports.

---

## Part 1: Competitor profiles

### 1. TeamLease RegTech (teamleaseregtech.com)

Heritage: founded as Avantis RegTech (2015); TeamLease Services took majority control (61.5%) in Nov 2021 and renamed it. Correction to common assumptions: Simpliance is NOT theirs (it sits under Aparajitha via Quess), and there is no product called "CompliantOne"; the legacy product is Avacom, now the "Reg*" family.

What they offer:
- RegTrack: core compliance management. Statutory compliance pre-configured from their database, internal compliance, license management, task management. Maker-checker, multi-layer approvals, reject/resubmit/revise, audit-only third-party roles, penalty and interest expense tracking, document management, notification and escalation engine.
- RegTrack Financial Institutions: BFSI edition built around RBI's Sep 2022 mandate that ML/UL NBFCs implement tech-based internal compliance monitoring. Adds: Reopening of Compliances (internal audit can reopen a closed item with observations), Deviation Workflow (CCO/Director-approved deviations with extended deadlines tracked), six-category tagging of every RBI obligation (Policy, Procedure, Disclosures, Customer Communication, Reporting, Automation), Comparative Analysis linking compliance IDs across old and new notifications to show full history, multi-regulator coverage (RBI, SEBI LODR, IRDAI corporate agents, NPCI TPAP, PMLA/FIU-IND, MCA).
- RegTrack-SDD: on-prem SEBI PIT Reg 3(5) Structured Digital Database of UPSI with time-stamping and tamper-proofing.
- RegUpdate: regulatory update feed and mobile app; claims ~3,700 government websites monitored daily, 24-96 hour turnaround.
- RegAuto-Labour and RegAuto-Secretarial: register/return/challan generation, board meeting automation, minutes and resolutions.
- RegService (managed compliance with 75-100+ in-house legal/CS/CA experts), RegAudit, Litigation Management, Contract Management, ICFR control testing, vendor/contractor compliance.
- Ria: AI regulatory information assistant chatbot, embedded contextual Q&A, explicitly not legal advice. Currently a support chatbot, not regulatory intelligence.

Target buyer: mid-to-large multi-entity, multi-state enterprises across 50+ industries; for the FI edition, explicitly the CCO of NBFCs. Public BFSI logos: Bajaj Finserv, Hero FinCorp, IndoStar, Motilal Oswal Wealth, InCred, Navi, Aavas, Satin, Toyota Financial Services and many more.

Standout UX/reporting ideas:
- Colour-coded "Smart Dashboard" with drill-down across 72+ parameters, filterable by FY, entity, location, period, user, act, risk level; six weekly report types auto-emailed.
- The RBI-mandate mapping table: the FI brochure maps each requirement of RBI's compliance-function circular to a specific RegTrack feature. The checklist itself is a sales weapon.
- Scale-Based Regulation walkthrough (BL/ML/UL/TL layers, per-segment obligations for MFI, gold loans, digital lending) in the brochure, but as PDF content, not an interactive product surface.
- Compliance taxonomy: 3 levels (Central/State/Local), 7 categories, 3 types (time/event/checklist), 12 artefact types (licenses, registrations, returns, registers, challans, displays, notices).

Pricing/positioning: no public pricing; modular packaging, no per-user licensing restriction, 1-week POC, 4-8 week implementation. Scale claims: 3,300+ entities, ~50,000 users, 1,536 Acts / 69,233 compliances / 6,618 filings, 50M+ compliances tracked, "reduced missed compliances by over 90%". Their moat is content + services + a listed parent. Their stated endgame is automation of filings (45% of obligations today, 70% target).

### 2. eQomply (eqomply.com)

Early-stage BFSI-native GRC startup (vendor entity QomplySuite; founder Pritesh Baviskar). Website stat counters literally show "0+" placeholders; zero reviews, zero named customers except one anonymized migration case (60,000+ tasks migrated). Pre-traction but strategically interesting.

What they offer:
- Pillars: Governance (policy management), Risk, Compliance, Privacy (DPDP), Integrations.
- Pre-mapped regulatory workflows for RBI, SEBI, IRDAI, CERT-In, DPDP; labour/POSH as an afterthought.
- RBI module: clause-wise library mapped to Master Directions, circular intake with applicability assessment per entity, multi-entity group tracking (NBFCs + payments bank + HFC in one group), inspection workflows with findings, responses and closure, board-ready reporting of status, exceptions and trends.
- SEBI module: workflows for brokers, AMCs, DPs, merchant bankers, IAs, RAs, PMS; consolidates circulars from SEBI, NSE, BSE, NSDL, CDSL; dedicated CSCRF cybersecurity tracking.
- IRDAI module: governance, outsourcing, investment norms, policyholder protection, "inspection readiness without the scramble".
- DPDP: DSR workflows, RoPA, versioned attested privacy policies linked to DPDP requirements.
- Cross-cutting: single dashboard across entities/regulators, escalation before items become audit findings, evidence auto-attached to tasks as work completes (timestamped, tamper-proof), regulatory-change intelligence mapping new requirements onto existing obligations.
- No AI features marketed anywhere.

Target buyer: BFSI multi-entity groups. Dedicated persona pages for CCO, CRO, DPO, CISO, Internal Audit, CS. The CCO page targets four pains: spreadsheet fragmentation, multi-regulator complexity, weeks-long quarterly board reporting, audit-time evidence scramble.

Standout UX/reporting ideas (their best asset):
- "Board-ready reporting in minutes" generated from live operational data via pre-configured filters and materiality criteria.
- Their board-dashboard design thesis: obligation coverage % by regulatory domain, overdue findings by severity and source with aging profiles, forward-looking emerging-regulation view, four-quarter trend lines instead of snapshots, and concentration risk in compliance ownership (single-point-of-failure obligations).
- "Evidence that exists before you ask for it": capture at the moment work happens.
- SEBI compliance calendar content marketing.

Pricing/positioning: custom pricing only, demo-led, no tiers. Effectively PolicyAI's closest thesis-competitor (regulator-native, BFSI-only) but without AI, without a graph, and without traction.

### 3. Ricago CMS (CLONECT Solutions, Bengaluru)

Note: parent is consistently Clonect Solutions, not "Knowledge Splice". Mentors/investors include T V Mohandas Pai. ISO and SOC 2 certified, Azure-hosted.

What they offer:
- Compliance Management System with 12-14 configurable modules: Compliance, Notice tracking, Registrations/Licenses renewal, Board Meeting (agendas, minutes, pre/post-meeting compliances), Event-based checklists, Risk Register, Litigation, Contracts, Declaration (functional heads self-certify departmental posture), Liaison, Bank Guarantees, Related Party Transactions, corporate document repository, assessments.
- Audit Management System (vendor audits with criticality scoring), Insider Trading Management System (SEBI PIT: trading windows, pre-approvals, UPSI declarations, deviation analytics between approvals and actual trades), Contracts & Obligations, Labour Compliance managed services, Ricago Pulse mobile app.
- Platform: 4-level escalations, email-based task responses, trend/heatmap/status dashboards, ERP APIs, SSO, automated regulatory update feeds, "AUOMS" applicability-filtering framework.
- AI: essentially none advertised. Content + workflow play.

Target buyer: mid-to-large multi-location Indian enterprises across 15+ industries; strong Company Secretary orientation (Board Meeting, RPT, ITMS modules).

Standout UX/reporting ideas:
- Unified senior-management dashboard marketed explicitly against RBI's Jan 31, 2024 internal-compliance-monitoring circular, with automated escalations and documented approvals for deviations.
- Criticality scoring of obligations by penalty severity (fine amount, imprisonment) to prioritize the library.
- Declaration module: bottom-up self-certification feeding board oversight.
- CMS+ managed-service model: Ricago's own experts operate the platform and produce MIS.

Pricing/positioning: quote-based only. Claims: 250+ clients, 10,000+ users, 1,500+ Acts, 35,000+ obligations, all 28 states. Reviewers note pricing is heavy for small orgs. BFSI is an overlay on a broad platform; no NBFC SBR views, no returns automation, no AML.

### 4. CladRysk (Moringa Techsolv, Mumbai)

Note: cladrysk.com does not resolve; everything lives on moringa-tech.com. Founded 2021, unfunded, founder Sanjeev Dahiwadkar; advisory board includes Prasanna Lohar (ex-DCB Bank). Only one named customer found (Shirpur Peoples Co-operative Bank, AML, 2022). Small, but the most BFSI-native module set of the six.

What they offer:
- CladRysk CMS: compliance calendar pre-configured for RBI inspection/audit cycles; obligation mapping to RBI, SEBI, IRDAI and internal standards; open/delayed/completed task views across branches and business units; automated escalation engine tied to task risk level; returns and statutory filing management that visualizes all Monthly/Quarterly/Yearly returns in one place; incident management with "AI-powered dashboards"; full audit trail; evidence-mapped document repository; no-code customization; cloud or on-prem.
- CladRysk AML: real-time transaction monitoring, sanctions/PEP/adverse-media screening with match scoring, automated STR/CTR/NTR/CCR/CBWT filing to FIU-IND, guided step-by-step alert processing, consolidated per-customer AML profiles.
- CladRysk Risk-Based Audit: built to RBI's RBIA master circular; audit priority by location/risk/history; reusable checklist libraries; carry-forward of unresolved non-compliances across cycles; root cause analysis with Pareto charts.
- Lending stack: LOS with KYC, collections mobile app, NPA/legal recovery, vendor management, video KYC.

Target buyer: exclusively BFSI: banks, NBFCs, urban and rural cooperative banks, MFIs, fintechs, insurers. Beachhead is clearly cooperative banks and mid-size NBFCs.

Standout UX/reporting ideas:
- Single-screen visualization of all M/Q/Y regulatory returns (the best returns-tracking UX story among the six).
- Branch and business-unit task rollups matching how RBI-regulated entities are organized.
- Pareto root-cause charts and audit non-compliance carry-forward.
- Notably missing from their marketing: any board pack or CCO dashboard artifact, and any SBR layer view.

Pricing/positioning: no public pricing ("flexible BFSI pricing"), no customer counts, thin press since 2023. Deep vertical stack, weak commercial traction.

### 5. KavachOne (KavachOne Solutions Pvt Ltd, Noida)

Founded 2023, unfunded. Half services (PCI DSS QSA audits, SOC 1/2, ISO 27001, UIDAI/Aadhaar audits, VAPT), half product. NOT a regulatory-obligation platform; a cybersecurity + DPDP privacy compliance firm. Adjacent competitor, not head-on.

What they offer:
- ConsentiQo: DPDP consent management. Purpose-granular consent lifecycle, DSAR automation via a customer-facing Privacy Rights Centre embedded in the banner, real-time consent analytics, audit trail with timestamp/IP/purpose, 7-year retention with unlimited exports, all 22 scheduled Indian languages, one-line integration.
- ComplyXpert: generic GRC (tracking, alerts, RBAC docs, "AI-driven risk assessments", policy versioning, incident and vendor monitoring), claims "30+ standards including RBI, SEBI, DPDP, GDPR, ISO 27001, HIPAA".
- PII Scanner, CDD Scanner (KYC-adjacent), RoPA/DPIA suite, TPRM.

Target buyer: startups, MSMEs, mid-market fintechs and merchants facing DPDP and PCI deadlines; DPO/CISO/founder persona, not the CCO/CS statutory persona. Enterprise ConsentiQo tier targets BFSI with India-hosted dedicated tenant.

Standout UX/positioning ideas:
- Speed-based packaging: "DPDP compliance in 2 weeks", "SOC 2 in 15 days".
- Flat, capped pricing with no per-consent fee (positioned against per-API-call CMPs); third-party mentions of bundles at USD 89-499/month.
- Compliance readiness ring ("88% SOC 2 Readiness") as the hero dashboard visual.

BFSI depth: shallow. RBI/SEBI/IRDAI appear only as audit-service line items. Their relevance to PolicyAI: they show what a credible DPDP module looks like and prove demand for DPDP + CERT-In readiness among fintechs.

### 6. Lexplosion (Komrisk)

Kolkata, operating since 2007, ISO 27001, 500-600+ clients, 10,000+ users, named clients include Asian Paints, Pidilite, Yamaha Motor India, plus "various BFSI entities".

What they offer:
- Komrisk (flagship): repository of 70,000+ compliance entries across central, state and municipal law, curated per entity; real-time regulatory updates auto-fetched from government sites pushed into client compliance lists (99% accuracy claim); Smart Compliance Calendar (date-based view of pending, missed, upcoming); maker-checker task workflows with dependencies; alerts with automatic escalation up to 10 levels (marketed specifically at the RBI mandate); evidence upload with audit trails and delay commentary; executive dashboards with drill-down; internal compliance module; "Ubiquitous AI" decision-support marketing; mobile apps with MFA and offline sync; ERP/HR APIs.
- Komtrol / Komtrol Plus: real-time stock-price monitoring and SEBI LODR Reg 30(11) market-rumour disclosure workflows (genuinely niche listed-company product).
- Komlit: litigation management with cause-list scraping and auto-updated hearing dates.
- Komplied: automated audit management. Komplify: SME product (site currently has an expired SSL cert, likely deprioritized).
- Services: regulatory audits, legislative monitoring, virtual in-house counsel, trainings (DPDP, POSH, PIT).

Target buyer: compliance officers, CS, legal heads of multi-entity mid-to-large enterprises; manufacturing/pharma/FMCG core with opportunistic BFSI positioning after the RBI mandate.

Standout UX/reporting ideas:
- The Smart Compliance Calendar as the primary operating surface.
- 10-level escalation matrix marketed 1:1 against RBI's Jan 2024 circular for ML/UL NBFCs.
- Update-to-obligation pipeline: regulatory update feed converted directly into client-specific task changes.

Pricing/reviews: the ONLY competitor with a public price signal: Capterra lists a starting price of INR 2,600/month, free trial, 4.0/5 from 15 reviews. Review cons: weak incident management, repetitive task generation needing manual cleanup, limited customization, hard for factory-level users. Breadth product; no evidence of master-direction-level granularity, no returns/CIMS support, no SBR views.

Market note: Complinity (complinity.com) surfaced repeatedly in NBFC compliance searches with dedicated BFSI/NBFC pages and is probably a closer seventh competitor worth a follow-up look.

---

## Part 2A: Feature-gap matrix, PolicyAI vs each competitor

Legend: Have / Partial / Missing. "TL" = TeamLease RegTech, "eQ" = eQomply, "Ric" = Ricago, "Clad" = CladRysk, "Kav" = KavachOne, "Kom" = Komrisk (Lexplosion).

| Capability | PolicyAI | TL | eQ | Ric | Clad | Kav | Kom |
|---|---|---|---|---|---|---|---|
| Multi-regulator source monitoring (crawl + updates) | Have (14 crawlers; some monitor feeds still disabled) | Have (~3,700 sites, human-curated) | Partial (curated intake) | Partial (update feeds) | Partial | Missing | Have (auto-fetch + curation) |
| Regulation knowledge graph (amends/supersedes lineage, as-of views) | Have (unique) | Partial (Comparative Analysis links compliance IDs across notifications) | Missing | Missing | Missing | Missing | Missing |
| AI obligation extraction from circulars | Have (unique, 6,900+ requirements) | Missing (human legal team) | Missing | Missing | Missing | Missing | Missing (marketing "AI" only) |
| Applicability mapping to org profile | Have (LLM-mapped, cited) | Have (parameter-based applicability engine) | Have (per-entity assessment) | Have (AUOMS filters) | Have | Missing | Have (curated library) |
| Policy-vs-regulation gap analysis with evidence passages | Have (unique) | Missing (RegAudit is a service) | Partial (unified control framework) | Missing | Missing | Partial (readiness scans) | Missing |
| Grounded AI chat with citations | Have (unique) | Partial (Ria chatbot, Q&A only) | Missing | Missing | Missing | Missing | Missing |
| Compliance calendar with statutory due dates | Missing | Have | Partial (content only) | Have | Have (RBI-cycle preconfigured) | Missing | Have (core surface) |
| Maker-checker + multi-level escalation matrix | Missing | Have (multi-layer, deviation workflow) | Have | Have (4 levels) | Have (risk-tiered) | Missing | Have (10 levels) |
| Evidence repository attached to obligations/tasks | Missing | Have (5M+ evidences) | Have (evidence-first thesis) | Have | Have | Partial (consent logs) | Have |
| Board / CCO one-click report pack | Missing | Partial (6 weekly reports, dashboards) | Have (board-ready reporting thesis) | Partial (Declaration + MIS) | Missing | Missing | Partial (exec dashboards) |
| Risk heatmaps / drill-down dashboards | Partial (KPIs + coverage %, no heatmap) | Have (72+ params, colour-coded) | Partial | Have (trends + heatmaps) | Partial (AI dashboards claim) | Partial (readiness ring) | Have |
| Registers / returns / filings tracking (RBI returns, challans) | Missing | Have (6,618 filings; register/challan generation) | Partial (regulatory reporting area) | Partial (licenses/registrations) | Have (M/Q/Y returns single screen) | Missing | Partial |
| License and registration renewal management | Missing | Have | Missing | Have | Partial | Missing | Partial |
| NBFC Scale-Based Regulation layer view (BL/ML/UL/TL) | Missing (EntityClass exists in graph, no SBR surface) | Partial (brochure content, curated sets, not interactive) | Missing | Missing | Missing | Missing | Missing |
| Controls + control testing | Partial (manual tests, no trends/alerts) | Have (ICFR module) | Have (unified controls) | Partial (risk register) | Partial (via audit) | Partial | Partial |
| Internal / RBIA-style audit management | Missing | Have (RegAudit, audit mgmt) | Have (internal audit workflows) | Have (AMS) | Have (RBIA-aligned, Pareto RCA) | Partial (services) | Have (Komplied) |
| AML / FIU-IND reporting (STR/CTR etc.) | Missing (FIU-IND crawled, no workflows) | Partial (PMLA obligations tracked) | Missing | Missing | Have | Partial (CDD scanner) | Missing |
| SEBI insider trading / SDD / LODR 30(11) | Missing | Have (RegTrack-SDD) | Partial (broker/AMC workflows) | Have (ITMS) | Missing | Missing | Have (Komtrol) |
| DPDP / privacy module (consent, DSAR, RoPA) | Missing | Missing | Have | Missing | Missing | Have (deepest) | Partial (training/services) |
| CERT-In / cyber compliance tracking | Partial (CERT-In crawled and extracted) | Partial | Have (CSCRF tracking) | Missing | Partial (cyber audit checklists) | Have | Missing |
| Litigation / notice management | Missing | Have | Missing | Have | Have (NPA/legal) | Missing | Have (Komlit) |
| Managed services / in-house legal content team | Missing (pure software) | Have (75-100+ experts) | Missing | Have (CMS+) | Missing | Have (audit arm) | Have |
| Mobile apps | Missing | Have | Missing | Have (Pulse) | Have (collections) | Missing | Have |
| Multi-entity / multi-tenant orgs | Have | Have | Have (group structures) | Have | Have | Partial | Have (70+ entities/client) |
| Granular RBAC + activity log | Missing | Have | Have | Have (SSO) | Have | Have | Have |
| Public pricing | Missing | Missing | Missing | Missing | Missing | Partial (flat bundles cited) | Have (INR 2,600/mo entry) |

Read of the matrix: PolicyAI owns the entire intelligence layer (graph lineage, AI extraction, gap analysis, grounded chat) that every incumbent lacks, and lacks almost the entire operations layer (calendar, escalations, evidence, returns, board pack) that every incumbent has. Indian buyers currently buy the operations layer because RBI told them to. The winning move is to keep the intelligence moat and build the minimum credible operations layer on top of data PolicyAI already has.

---

## Part 2B: The 9 highest-leverage features to leapfrog

Ordered by leverage (deal impact divided by effort).

### 1. Compliance calendar with statutory due dates
- What: a month/quarter grid of every dated obligation for the org: statutory due dates extracted from regulations (Deadline nodes, HAS_DEADLINE edges), recurring frequencies already on mapped obligations (monthly/quarterly/annual), task due dates, and license renewals later. Views: upcoming, overdue, completed; filter by regulator, severity, owner.
- Why it wins in India: it is the primary operating surface of Komrisk, CladRysk and Ricago, and the first thing every compliance head asks to see in a demo. Its absence marks PolicyAI as "insights tool", not "system of record". No deal closes without it.
- Effort: S to M. The data largely exists; this is a new page plus a due-date materialization job (obligation frequency -> next-occurrence dates).
- Built from: Deadline nodes, HAS_DEADLINE edges, obligation frequency and severity, tasks.

### 2. Board / CCO one-click report pack
- What: a button that renders a dated, exportable (PDF/HTML) board pack: coverage % by regulator and domain, gap counts by severity with aging, four-quarter trend lines, new regulations this quarter with impact summaries, overdue tasks and control failures, ownership concentration (obligations that depend on one person), and an auto-drafted executive narrative from the Copilot. Steal eQomply's thesis (trends not snapshots, aging profiles, concentration risk) and actually ship it.
- Why it wins: RBI's compliance-function circulars require periodic reporting to the Board/ACB; every CCO assembles this by hand quarterly today. eQomply's entire pitch is this pack and they have no product traction; TeamLease has dashboards but no one-click artifact. This is also the feature the economic buyer (Board) personally sees.
- Effort: M. Rendering and narrative generation; all inputs are queries over existing tables.
- Built from: gaps, obligations, coverage rollup, alerts, tasks, control_tests, plus Copilot for the narrative.

### 3. RBI Scale-Based Regulation layer view for NBFCs
- What: org profile gains an SBR layer (Base/Middle/Upper/Top) and sub-class (ICC, MFI, HFC, P2P, gold, digital lending). The obligations page, graph explorer and calendar filter by layer; a dedicated view shows "your layer vs the layer above" so a growing NBFC can see what crossing INR 1,000 crore adds. Graph APPLIES_TO edges get layer-qualified.
- Why it wins: nobody has this as an interactive surface. TeamLease documents SBR only in a sales PDF. Every ML/UL NBFC conversation starts with "which directions apply to my layer", and the 2023 consolidated Master Direction for NBFCs is organized by layer. It is also a perfect demo of the graph moat: a visual layer diagram no checklist vendor can fake.
- Effort: M. Requires tagging EntityClass/APPLIES_TO with SBR layers (LLM-assisted re-extraction pass over RBI corpus) plus UI.
- Built from: EntityClass nodes, APPLIES_TO edges, org profile, obligations.

### 4. Regulatory-change impact timeline (impact assessment on every new circular)
- What: for any new circular: an auto-drafted impact assessment (already planned as quick-win B1) plus a timeline visualization: the lineage chain (what it amends/supersedes, effective dates, transition windows) rendered horizontally, with the org's affected obligations, gaps and tasks pinned to dates. "This circular changes 14 of your obligations, opens 3 gaps, and your policy X cites the superseded version."
- Why it wins: this is the one thing only a knowledge graph can do, and it converts PolicyAI's most defensible asset into a daily-use feature. Incumbents push a text update into a task list; none can show that a policy cites a superseded circular. It is the demo moment that ends evaluations.
- Effort: M. Graph queries + a timeline component + the B1 drafting endpoint.
- Built from: AMENDS/SUPERSEDES/REFERENCES edges, obligation mappings, gaps, policy citations, alerts.

### 5. Escalation matrix + maker-checker workflows (RBI-mandate checklist page)
- What: tasks gain a checker step and configurable escalation levels (owner -> compliance head -> CCO -> Board) with auto-escalation on breach, deviation approval with documented reason (TeamLease's Deviation Workflow), and an audit trail. Ship alongside a public "RBI circular requirement vs PolicyAI feature" checklist page, copying TeamLease's brochure device.
- Why it wins: RBI's Jan 31, 2024 circular explicitly requires workflow-based monitoring with escalation and documented deviation approval for ML/UL NBFCs. Komrisk sells "10 escalation levels" as a headline. Without this, PolicyAI fails NBFC procurement checklists regardless of how good the intelligence is. Table stakes, not differentiation.
- Effort: M. Task model extension + notification rules + an approvals UI.
- Built from: tasks, alerts, orgs/users (needs role field addition).

### 6. Risk heatmap (severity x regulator / business function)
- What: a matrix heatmap: rows = regulator or compliance domain (KYC, capital, IT/cyber, conduct), columns = severity or status; cells coloured by open gap/overdue count, click-through to the filtered gap list. A second view: branch/entity rollup for multi-entity orgs (CladRysk's branch rollup idea).
- Why it wins: Ricago and TeamLease lead demos with colour-coded dashboards; CCOs think in heatmaps because RBI's own risk-based supervision does. Cheap credibility.
- Effort: S. Pure aggregation over existing data plus one component.
- Built from: gaps (severity, status, topic), obligations (regulator, domain), tasks (overdue).

### 7. Registers, returns and filings tracker
- What: a curated dataset of statutory returns and filings per entity class (RBI returns via CIMS: DNBS returns for NBFCs, SFB/UCB returns; SEBI intermediary reports; FIU-IND reports; MCA annual filings), each with frequency and due date, joined to the calendar and to evidence upload. CladRysk's single-screen M/Q/Y returns view is the UX to beat.
- Why it wins: "returns" is what compliance teams are actually fined for missing. TeamLease claims 6,618 filings; CladRysk leads with the returns screen. This converts PolicyAI from "policy gap tool" to "the thing that keeps me out of trouble monthly".
- Effort: L. The engine is the calendar (feature 1); the hard part is curating and maintaining the returns catalogue per entity class. Start with NBFC-ML returns only (approx. 20-30 returns) to keep it M-sized for the beachhead.
- Built from: EntityClass + org profile for applicability, new returns catalogue table, calendar engine, tasks for evidence.

### 8. Evidence-first audit trail and export
- What: attach evidence files to tasks, gaps closures and control tests at the moment of completion, timestamped and immutable; one-click export of the full trail (policy versions, approvals, gap history, evidence index) for an RBI inspection. eQomply's "evidence that exists before you ask for it".
- Why it wins: the RBI inspection scramble is the single most painful week of a compliance head's year, and evidence trails are what auditors accept. Every incumbent has an evidence store; PolicyAI has none, and it also closes the internal audit-trail-export gap (B6).
- Effort: M. File storage + linkage model + export job (Supabase storage exists).
- Built from: tasks, gaps, control_tests, policy_versions; new evidence table.

### 9. DPDP + CERT-In readiness packs
- What: two packaged obligation sets: DPDP Act + Rules mapped as first-class obligations (consent, notice, DSAR, breach reporting, DPO, significant data fiduciary tests) and CERT-In directions (6-hour incident reporting, log retention, KYC of subscribers) with gap analysis against the org's uploaded privacy/IT policies, and a readiness-score ring (KavachOne's visual).
- Why it wins: DPDP Rules enforcement makes this the top budgeted item for fintechs in 2026, and CERT-In is already in PolicyAI's crawl corpus. KavachOne proves willingness to pay flat monthly fees for exactly this; none of the BFSI-obligation incumbents cover it well. It is also the natural wedge for the pre-license fintech persona who cannot yet use RBI modules.
- Effort: S to M. It is content curation + existing gap-analysis machinery, no new engine.
- Built from: CERT-In crawled corpus, DPDP corpus (eGazette ingestion), existing extraction + mapping + gap pipeline.

Deliberately deprioritized: AML transaction monitoring (CladRysk's turf, a different product category), insider-trading SDD (niche, on-prem expectations), litigation management, mobile apps, managed services. Also recommended but not a feature: publish pricing. Only Komrisk shows a number (INR 2,600/mo entry) and every other vendor hides behind demos; a transparent self-serve tier would be a genuine differentiator for the fintech and small-NBFC segments.

---

## Part 2C: Persona validation

### Persona 1: Compliance head at a Middle-Layer NBFC (e.g. INR 2,500 crore AUM lender, 40 branches)

Day 1 expectations: which RBI Master Directions and circulars apply to an ML NBFC of my type; a calendar of my returns (DNBS via CIMS) and dated obligations; a workflow that satisfies the Jan 2024 RBI circular (maker-checker, escalation, deviation approval) because inspectors now ask to see it; a dashboard the CCO can screenshot for the Board.

What PolicyAI gives today: strong start on applicability (obligations mapped to profile with severity and citations), genuinely better change intelligence than anything they have seen, gap analysis against their Fair Practices Code and KYC policy that would take a consultant weeks.

Issues they hit, concretely:
1. No SBR layer filter: they must trust that "nbfc" profile mapping caught layer-specific items like the ML exposure norms. They will spot-check, find an Upper-Layer-only item mapped to them (or a missed ML item), and their confidence drops sharply. LLM mapping errors are existential for this persona.
2. No calendar and no returns list: their current Excel tracker, ugly as it is, tells them what is due Friday. PolicyAI does not. They will keep the Excel, and the tool that keeps the Excel alive loses the renewal.
3. No maker-checker/escalation: fails the literal text of the RBI circular, so PolicyAI cannot be their compliance monitoring system of record, only a supplement, which halves the budget available.
4. No evidence attachment: come inspection, PolicyAI holds none of their proof.
Features that close it: 3 (SBR view), 1 (calendar), 7 (returns), 5 (escalation + RBI checklist page), 8 (evidence). With those five, PolicyAI beats TeamLease FI on intelligence and matches it on the mandate checklist.

### Persona 2: CCO at a small bank (SFB or large UCB)

Day 1 expectations: quarterly board/ACB compliance report preparation (their single biggest recurring task); inspection readiness (RBS/SPARC data calls, evidence retrieval); tracking circulars across RBI, FIU-IND, CERT-In and, if listed, SEBI LODR; branch-level compliance rollups.

What PolicyAI gives today: multi-regulator crawl coverage is genuinely wider than incumbents' BFSI sets (CERT-In, FIU-IND, NPCI already ingested); Copilot answers "what changed for us this month" with citations, which is exactly the board-pack raw material; coverage % is a start.

Issues they hit:
1. No board pack: they will ask "can it produce my ACB report" in the first meeting. Today the answer is "you can copy-paste from the dashboard", which loses to eQomply's pitch even though eQomply barely exists.
2. No branch dimension: a 200-branch bank thinks in branch rollups (CladRysk's model); PolicyAI's org model has no locations.
3. No activity log / granular RBAC: bank IT procurement will fail the vendor assessment on this alone, before features are even discussed. Also no SSO.
4. Controls exist but tests are manual records with no trends and no failure alerts; a CCO will call the controls module "a register, not monitoring".
Features that close it: 2 (board pack, the deal-maker), 6 (heatmap with entity/branch rollup), 8 (evidence + export), plus the non-feature platform work (RBAC, activity log, SSO) that this persona makes unavoidable. Realistically PolicyAI should treat small banks as the second beachhead after NBFCs because of the procurement bar.

### Persona 3: AIF / fund operations lead (Cat II AIF, small ops team, CS on retainer)

Day 1 expectations: SEBI AIF Regulations + circulars applicable to their category; the compliance test report and quarterly reporting calendar (SI portal filings, PPM audit, valuation timelines); changes consolidated from SEBI and, ideally, custodian/depository circulars; something cheap, because the team is 3 people.

What PolicyAI gives today: SEBI corpus with lineage is genuinely useful (AIF circulars amend constantly and the consolidation pain is real); AIF exists as an EntityClass; Copilot with citations replaces half their outside-counsel quick questions.

Issues they hit:
1. Coverage doubt: eQomply consolidates NSE/BSE/NSDL/CDSL circulars; PolicyAI does not crawl exchanges/depositories, and fund ops live partly on those. They will find a missing NSDL circular in week one.
2. No filings calendar: the AIF compliance year IS a calendar (quarterly SI portal reports, annual compliance test report, PPM audit). Without feature 1 + 7 the product is a research tool to them.
3. Category granularity: Cat I vs II vs III obligations differ materially; same mapping-precision risk as the NBFC layer problem, solved by the same applicability-qualification work as feature 3.
4. Price sensitivity: they will not sit through enterprise sales. A self-serve tier with published pricing wins this segment almost by default since every incumbent is quote-only.
Features that close it: 1 (calendar), 7 (SEBI filings catalogue), 4 (change timeline for amended AIF circulars), plus exchange/depository crawlers and public pricing.

### Persona 4: Fintech founder, pre-RBI-license (applying for PA authorisation or NBFC registration)

Day 1 expectations: a roadmap: what does an RBI PA licence (or NBFC CoR) require of me, what must be true before application (net worth, governance, IT), what applies on day one after; DPDP and CERT-In obligations that already bind them today; something a non-compliance person can understand; low cost.

What PolicyAI gives today: the graph explorer and Copilot are genuinely great here ("what applies to a payment aggregator" with citations beats a week of law-firm memos); CERT-In content is already ingested.

Issues they hit:
1. No "future entity" mode: the org profile assumes you ARE a regulated entity. A pre-license founder needs "show me obligations as if I were a PA", plus a readiness checklist against licensing criteria. Today they must fake a profile and get no application-stage guidance.
2. DPDP absent: the one regime that binds them today regardless of license is not a packaged module; they will bounce to KavachOne or a DPDP point tool for the urgent need and never come back.
3. Overwhelm: 6,900 requirements and a force graph impress but do not answer "what are my 12 next actions". Severity exists; a curated stage-based checklist does not.
4. No pricing page: a founder will not book an enterprise demo. They churn silently.
Features that close it: 9 (DPDP + CERT-In packs, their entry drug), 3 generalized into "prospective entity-class simulation" (the same layer-qualified applicability engine), 1 (calendar, once licensed), and a published self-serve tier. This persona is also the cheapest acquisition channel: they grow into the Persona 1 NBFC customer.

### Cross-persona verdict

All four personas share the same first collision: PolicyAI analyses brilliantly but does not yet operate anything (no calendar, no evidence, no escalation, no report artifact), while every incumbent operates adequately and analyses barely. Features 1, 2 and 5 are table stakes across all personas; features 3, 4 and 7 are the moat-converters that no competitor can copy quickly because they require the graph; features 6, 8 and 9 are fast credibility wins. Sequencing recommendation: 1 -> 6 -> 2 -> 5 -> 3 -> 4 -> 8 -> 9 -> 7, which front-loads small efforts that unblock demos while the graph-native differentiators are built.

---

## Appendix: key sources

- TeamLease RegTech: teamleaseregtech.com (product, FAQs, about), RegTrack FI brochure (cdn-static.teamleaseregtech.com/static/pdf/RegTrack_Financial_institution_brochure.pdf), business-standard.com (rename PR), bizzbuzz.news CEO interview, teamleaseregtech.com/case-studies/NBFC-compliances-housing-finance
- eQomply: eqomply.com (regulations/rbi, regulations/sebi, solutions/for-compliance-leaders, blog/compliance-dashboard-board, blog/sebi-compliance-calendar), capterra.in/software/1077242/eQomply, softwarefinder.com profile
- Ricago: ricago.com (product/compliance-management-system-india, about-us, blog on RBI guidelines), softwaresuggest.com/ricago-cms and /ricago-itms, capterra.com/p/146346/ricago
- CladRysk / Moringa Techsolv: moringa-tech.com (grc.php, compliance-monitoring-system.php, anti-money-laundering.php, risk-based-audit.php, about.php), Tracxn profile, mediabrief.com Shirpur partnership
- KavachOne: kavachone.com (product, ConsentiQo, ComplyXpert, RegulatoryCompliance, about-us), Tracxn profile
- Lexplosion / Komrisk: lexplosion.in (compliance-management-software, products-services/compliance/komrisk, RBI-mandate posts), capterra.com/p/172823/Komrisk, legaltechnologyhub.com vendor profile, Play Store Komrisk app
- PolicyAI internal: /Users/nishantkumar/policyai/docs/FEATURE_ALIGNMENT.md, PROJECT_CONTEXT.md, frontend/src/app/(app)/ pages
