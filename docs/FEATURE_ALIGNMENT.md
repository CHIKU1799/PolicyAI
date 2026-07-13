# Landing page vs product: feature alignment audit

Audited 2026-07-13 against the live codebase (`main` @ `80b5973`). Each claim on the
marketing landing page is graded: **SHIPPED** (claim is true today), **PARTIAL**
(core exists, specific sub-claims missing), **MISSING** (not built), or **OVERCLAIM**
(cannot be made true by building; the copy must change).

## Module claims

### 01 Horizon scanning: PARTIAL
| Claim | Reality |
|---|---|
| "Continuously monitor 240+ regulatory sources" | 16 seeded monitoring sources, 4 enabled (RBI, SEBI x2, IRDAI). 12 more (PFRDA, IFSCA, NPCI, FIU-IND, RSS feeds) seeded but disabled pending feed verification. |
| "in real time" | Render cron crawls every 6 hours. Realtime alerts exist in-app once ingested (Supabase Realtime). |
| "Real-time AI alerts with impact scoring" | Alerts exist (NEW_REGULATION etc.) with LLM-assigned severity. No numeric impact score. |
| "Multi-jurisdiction source coverage" | India only (by design; the landing page mock even shows FCA, a UK regulator). |
| "Daily digest, ranked by what matters" | `notifications.py` can send per-alert emails when configured. No daily digest job. |

### 02 Change -> structured obligations: SHIPPED
Extraction pipeline turns every document into discrete requirements (6,900+ so far),
obligation mapping links them to the org profile with citations, severity, frequency,
evidence expected. Traceability from rule to obligation to task is real. Owner
assignment exists via tasks (gbrain enrichment optional).

### 03 Gap analysis: SHIPPED (one soft spot)
Requirement-level gaps with coverage_status (covered/partial/missing/conflicting),
the exact policy passage as citable evidence, severity triage, and AI-written
`remediation_plan` per gap. Soft spot: "coverage scoring per requirement" is a
4-state classification, not a numeric score; fine, but there is no rollup
"coverage %" anywhere in the UI.

### 04 Controls testing & monitoring: PARTIAL
Control + ControlTest models and a controls page (effectiveness KPIs, latest test
per control) exist. Missing vs claims:
- "Continuous, automated testing": tests are manual records; nothing runs them.
- "30-day effectiveness trends": no trend chart (control_tests carry the data).
- "Alerts the moment a control fails": no alert is emitted on a failed test.

### 05 Policy governance: PARTIAL (closer than expected)
Policy + PolicyVersion (immutable snapshots, version_no, review/approval state,
approved_by/at) and a policies page listing version history. Missing vs claims:
- "Multi-step approval workflows": single approve step, no workflow chain.
- "Immutable, exportable audit trail": versions are immutable but there is no export.

### Copilot: SHIPPED (one headline overclaim)
`/ask` agent with 7 grounded tools (hybrid RRF regulation search, obligations,
requirements, tasks, insights, profile) and citations back to source. The top
banner claim "PolicyAI Copilot now drafts impact assessments automatically" is
NOT built: nothing drafts an impact assessment today.

## Trust strip / stats / enterprise section

| Claim | Verdict |
|---|---|
| "240+ regulatory sources monitored" | OVERCLAIM today (16 seeded / 4 live). Either enable + expand sources or change the number. |
| "85% less manual triage time", "99.1% obligation SLA met", "<2h alert to mapped obligation" | OVERCLAIM: nothing measures these. <2h alert-to-obligation is actually plausible with MAP_AFTER_SCAN; the others are unverifiable marketing. |
| "SOC 2 Type II", "ISO 27001", "GDPR" badges | OVERCLAIM: no certifications. Must be removed or reworded ("built with SOC 2-ready practices" at most). |
| "SSO & SCIM (SAML)" | MISSING: Supabase email+password only. Supabase supports SAML SSO on paid tier if wanted later. |
| "Data residency: UK, EU and US regions" | OVERCLAIM: single Supabase region, and the product targets India (ap-south would be the honest region). |
| "Role-based access: granular permissions, full activity logging" | PARTIAL: orgs + platform-admin exist; no granular roles, no activity log. |
| Logos (Meridian, Northgate...) and testimonial (Dana Locke, Northgate Bank) | Fictional placeholders; fine for a mock, must go before real customers see it. |
| FCA / Mortgages / PS23/12 examples throughout the mocks | Jurisdiction mismatch: product is RBI/SEBI/IRDAI. Swap for Indian examples (nbfc_mfi, Digital Lending Directions, KYC Master Direction). |

## Alignment plan

Two levers: build the missing features (B-items) and fix copy that cannot be true (C-items).

**Quick wins, build (each roughly a half-day or less):**
- B1. Impact-assessment drafting: Copilot endpoint + button on a regulation that
  drafts a structured impact assessment (affected obligations, gaps, suggested
  actions) from the graph + org profile. Kills the banner overclaim.
- B2. Control-failure alert: emit an Alert (and email if configured) when a
  ControlTest is recorded with result=failed / effectiveness flips to ineffective.
- B3. Effectiveness trend: small sparkline/chart on the controls page from
  control_tests history.
- B4. Coverage rollup: "X% of requirements covered" KPI on dashboard + gaps page.
- B5. Daily digest: cron endpoint that emails a ranked summary of the last 24h
  (new regulations by severity, new gaps, overdue tasks).
- B6. Audit trail export: CSV export of policy_versions + approvals + gap history.

**Copy fixes on the landing page (C-items, one pass):**
- C1. "240+" -> honest number or "RBI, SEBI, IRDAI & more"; drop "real time" for
  "every 6 hours" or "continuous".
- C2. Remove SOC 2 / ISO 27001 / GDPR badges and the data-residency card; replace
  with real security facts (Supabase RLS, encrypted at rest, org isolation).
- C3. Replace FCA/Mortgages mocks and stats with Indian examples and real corpus
  numbers (documents ingested, requirements extracted, graph size).
- C4. Remove fictional logos/testimonial or mark as illustrative.
- C5. SSO & SCIM card -> "Roadmap" tag, or drop.

**Bigger builds (defer unless prioritized):** verify + enable the 12 dormant
sources and add more regulators (moves toward the big sources number), granular
RBAC + activity log, multi-step approval chains, automated control testing.
