# How Compliance Mapping Works — End-to-End

This is the canonical description of how a raw regulatory document becomes an
actionable compliance obligation in PolicyAI, and how the pieces align. Read it
alongside `PROJECT_CONTEXT.md` (scope) and the package docstrings (detail).

## The pipeline at a glance

```
                ┌── crawlers (policyai_scrapers) ──┐
  sources ─────►│  RBI · SEBI · IRDAI · MCA ·      │
  (16 seeded)   │  PFRDA · IFSCA · NPCI · FIU-IND  │──┐
                │  + RSS feeds (tax/trade/cyber)   │  │   manual / Drive
                └──────────────────────────────────┘  │   ingestion
                                                       ▼   (policyai_extraction.ingest)
                                            ┌────────────────────┐
                                            │   RawDocument      │  source + source_id (dedup key)
                                            └─────────┬──────────┘
                                 process_document (extraction pipeline)
                                                      ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │  REGULATION node  +  Requirements[]  +  edges                    │
        │  ISSUED_BY · APPLIES_TO(entity classes) · COVERS_TOPIC ·         │
        │  HAS_DEADLINE · AMENDS/SUPERSEDES/REFERENCES                     │
        │  effective_from = stated effective date | published date        │
        └─────────────────────────────┬───────────────────────────────────┘
                          map_unmapped → map_obligation  (per org)
                                        ▼
   relevance gate ── company profile (entity classes ∪ parents, topics, regulators)
        │  no match → skip (no LLM cost)
        ▼ match
        ┌─────────────────────────────────────────────────────────────────┐
        │  OBLIGATION  (severity, type, frequency, citation, confidence)   │
        │   ├─ Requirement-level GAPs   (grounded vs. company policy KB)   │
        │   ├─ Obligation-level gap summary                                │
        │   ├─ TASKS  (owner, due date, priority)                          │
        │   └─ AuditEvent + NEW_OBLIGATION alert (only when truly new)     │
        └─────────────────────────────┬───────────────────────────────────┘
                                       ▼
                         insights (prioritized "what needs attention")
                         timeline / as-of (point-in-time posture)
                         ask agent (grounded Q&A over all of the above)
```

## Stage by stage

### 1. Acquisition — two doors, one schema
- **Crawlers** (`policyai_scrapers`): one `MonitoringSource` per regulator endpoint;
  the runner crawls due sources, dedups on `source_id` via an incremental watermark
  (it does not re-fetch known documents), and persists `RawDocument`s.
- **Manual / Drive ingestion** (`policyai_extraction.ingest`): pre-fetched text
  (e.g. RBI notification PDFs) becomes `RawDocument`s through the *same* path. A
  hand-fed document and a crawled one are indistinguishable downstream.
- Both dedup on `(source, source_id)`, so re-runs are idempotent.

### 2. Extraction — document → graph (`pipeline.process_document`)
Forced-tool Claude extraction (`claude-sonnet-4-6`) yields an `ExtractedRegulation`,
which becomes a **REGULATION node** plus:
- **Requirements** — the atomic, objective mandates of the document (shared across
  orgs), each with type / citation / evidence / penalty.
- **Edges** — `ISSUED_BY` (regulator/department), `APPLIES_TO` (seeded entity
  classes only), `COVERS_TOPIC` (topics, created on demand), `HAS_DEADLINE`, and
  `AMENDS / SUPERSEDES / REFERENCES` when the target regulation already exists.
- **Valid-time anchor**: `effective_from` = stated effective date, else publication
  date. Supersession/amendment retires the predecessor and cascades (see §6).

### 3. Relevance gate — who does this apply to? (`mapping.map_obligation`)
Before spending on the expensive mapping model, intersect the regulation with the
**company profile**:
- entity classes (expanded with parents — an NBFC-MFI is also an NBFC),
- topics, and
- regulators (a topic-only match must come from a regulator the company is subject
  to, to kill incidental cross-regulator false positives).

No match ⇒ return without an LLM call. This is what keeps mapping cost bounded even
across hundreds of newly ingested regulations.

### 4. Obligation mapping — graph → action (`claude-opus-4-8`)
For relevant regulations, the mapping model produces an **Obligation** (severity,
type, frequency, citation, penalty, `mapping_confidence`, one-line rationale) plus:
- **Requirement-level gaps**: per-requirement coverage vs. the company's policy KB
  (pulled by pgvector + optional rerank). Gap descriptions are **grounded** — if the
  model's text shares no content with the requirement or the policy excerpts, it is
  rejected and replaced with requirement-derived text (no hallucinated gaps persist).
- **Tasks**: concrete actions; a re-map preserves human progress (only untouched
  TODO tasks are swept) and never duplicates an owned task.
- **Audit + alert**: an `AuditEvent` carrying the calibration signal
  (confidence / low-confidence / ungrounded-gap count); a `NEW_OBLIGATION` alert
  fires only when the obligation is genuinely new.

### 5. Surfacing
- **Insights** (`insights.compute_insights`): one prioritized feed both the
  dashboard and the Ask agent consume, so numbers always agree.
- **Timeline / as-of** (`/timeline/as-of/{date}`): point-in-time posture from the
  bitemporal model — what was in force on any date, not just "now".
- **Ask agent**: grounded Q&A (hybrid vector + FTS retrieval) over the whole graph.

### 6. Bitemporal alignment
Supersession (`graph_ops.supersede_node`) closes the validity of the old
regulation **and** cascades to its requirements, obligations, and gaps, stamping
`valid_to` / `invalidated_at`. So a point-in-time query never returns an obligation
from a dead regulation, and "as of last March" reconstructs the real posture.

## How the stages are wired (no orphaned steps)

The seam that used to be manual — *crawl ingests regulations but mapping was a
separate CLI* — is now closed:

| Trigger | What runs | Mapping included? |
|---|---|---|
| `make crawl` / `POST /scan` / cron | crawl → extract → **map** | Yes, when `MAP_AFTER_SCAN` (default **on**) |
| `make ingest FILE=… --map` | ingest → extract → **map** | Yes, with `--map` |
| `make ingest FILE=…` | ingest → extract | No (map later) |
| `make map` / `POST /map` | map unmapped regulations | — |

`MAP_AFTER_SCAN=false` keeps crawl and mapping decoupled if you want to control the
(opus) mapping spend separately. All mapping paths share one core
(`map_all.map_unmapped_in_session`), so behaviour is identical however it's invoked.

## Cost & safety alignment
- Extraction = `claude-sonnet-4-6`; mapping = `claude-opus-4-8` (billed to
  `ANTHROPIC_API_KEY`). Embeddings = Cohere (`COHERE_API_KEY`). Both metered.
- The relevance gate means most newly ingested regulations cost **nothing** to map.
- Every mapping path is per-regulation isolated and idempotent.
- Backups: `make export-graph` (portable JSON of the whole compliance state) and
  `make backup` (native `pg_dump`); Supabase PITR covers physical recovery.
