# PolicyAI

Regulatory-compliance intelligence platform for India (FiscalNote / Zango-style).
Continuously monitors RBI, SEBI, IRDAI, and MCA; extracts structured regulations
into a knowledge graph; maps obligations against each company's uploaded policies;
and generates actionable tasks — behind a professional dashboard.

See [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) for the original 2-week graph
spec. This README documents the cloud build.

## Architecture (three tiers)

```
 VERCEL          Next.js 14 dashboard — KPIs · obligations · tasks · KB · graph · live alerts
   │  @supabase/ssr (reads, RLS, Realtime)        │ fetch (heavy ops)
 SUPABASE        Postgres15 + pgvector (graph DB) · Auth · Storage · Realtime · pg_cron + pg_net
   │  pg_net trigger on new regulation            ▲ writes back
 RENDER          Python worker — FastAPI (doc processing, mapping, graph) + cron crawler (Playwright)
```

The crawler + Claude pipeline can't run on Vercel (Playwright, long jobs), so the
worker tier is a separate always-on Render service. Embeddings default to a
self-hosted Hugging Face **bge-m3** endpoint (1024-dim, matches the schema).

## Layout

```
policyai/
├── render.yaml               # Render worker (FastAPI) + cron crawler
├── supabase/migrations/      # platform SQL: extensions, Realtime, pg_net trigger
├── .devcontainer/            # GitHub Codespaces (zero local footprint)
├── pyproject.toml            # uv workspace root
├── packages/
│   ├── scrapers/             # Playwright: rbi/sebi/irdai/mca + runner (the monitoring agent)
│   ├── extraction/           # Claude llm + bge-m3 embeddings + pipeline + obligation mapping + gbrain adapter
│   ├── graph/                # SQLAlchemy 2.0 async + Alembic + pgvector (graph + 7 app tables)
│   └── api/                  # FastAPI worker: /documents /profile /internal /graph
└── frontend/                 # Next.js 14 app router + Tailwind + shadcn-style UI
```

## Prerequisites

- A **Supabase** project (Postgres + pgvector + Storage + Realtime)
- A **Render** account for the worker tier (or run the worker locally)
- An HF Inference Endpoint serving `BAAI/bge-m3`, plus an Anthropic API key
- Python 3.11+, [uv](https://github.com/astral-sh/uv), Node.js 20+
- Optional: develop entirely in the cloud via **GitHub Codespaces** (`.devcontainer/`)

## Quickstart

```bash
cp .env.example .env              # fill in Supabase DSN/keys, ANTHROPIC + HF keys

# 1. One-time Supabase platform setup (SQL editor or supabase CLI):
#    run supabase/migrations/0000_platform.sql   (extensions + Realtime)
#    run supabase/migrations/0001_triggers.sql   (new-regulation -> mapping hook)

make install                      # uv sync — installs all 4 workspace packages
make db-migrate                   # alembic upgrade head  (against Supabase)
make db-seed                      # regulators, entity classes, acts, monitoring sources

make crawl                        # one monitoring pass (Playwright -> graph)
make dev-api                      # FastAPI worker on :8000
make dev-web                      # Next.js dashboard on :3000  (or: cd frontend && npm run dev)
```

The Render cron runs `python -m policyai_scrapers.runner` on a schedule; the web
service runs `uvicorn policyai_api.main:app`. Both are defined in `render.yaml`.

## Makefile targets

| Target       | What it does |
|--------------|-----------------------------------------------------|
| `install`    | `uv sync` — install Python workspace |
| `test`       | `uv run pytest` across all packages |
| `lint`       | `ruff check` + `black --check` |
| `format`     | Auto-fix with `ruff --fix` and `black` |
| `db-migrate` | `alembic upgrade head` (against Supabase) |
| `db-seed`    | Insert regulators, entity classes, acts, monitoring sources |
| `crawl`      | Run one monitoring pass over all enabled sources |
| `dev-api`    | Run the FastAPI worker locally (:8000) |
| `dev-web`    | Run the Next.js dashboard locally (:3000) |
| `db-up/down/reset` | Optional local Postgres via docker compose (offline dev) |

## Running integration tests

The `graph` package tests hit a real Postgres with pgvector. Point them at a
throwaway DB via `TEST_DATABASE_URL`:

```bash
# create the test DB once
docker exec -it policyai-postgres \
  psql -U policyai -c "CREATE DATABASE policyai_test"

export TEST_DATABASE_URL="postgresql+asyncpg://policyai:policyai@localhost:5432/policyai_test"
uv run pytest packages/graph/tests
```

Tests reset the schema and re-apply `alembic upgrade head` once per session,
then run CRUD, JSONB, pgvector similarity, and seed-idempotence checks.

## Code conventions

- Black + ruff, line length 100, strict type hints
- All LLM calls route through a single client wrapper (see
  `packages/extraction`) with retry and cost tracking
- Prompts live in `prompts/` as versioned files with eval results
- Extractions are validated against Pydantic models before DB writes

## End-to-end flow

1. **Monitor** — Render cron crawls RBI/SEBI/IRDAI/MCA → dedup via
   `RawDocument.content_hash` → new docs only.
2. **Extract** — Claude turns each doc into a structured regulation → upserts
   graph nodes/edges (APPLIES_TO / COVERS_TOPIC / HAS_DEADLINE / …) + embedding →
   writes an alert.
3. **Onboard** — a company uploads policies to the Knowledge Base; the worker
   extracts text, embeds, and derives a `company_profile`.
4. **Map** — a new regulation triggers obligation mapping (graph traversal +
   pgvector gap evidence + Claude) → `obligations` + `tasks`, surfaced live.
5. **Act** — the dashboard shows KPIs, obligations with gap analysis, a task
   board, the knowledge graph, and a realtime alert feed.

## Status

Single-org MVP built end-to-end across all six phases (cloud schema, monitoring
agent, LLM/embeddings, knowledge base, obligation mapping, dashboard). Next:
multi-tenant Auth + RLS, live scraper-selector tuning against current DOM, and an
eval set for extraction accuracy.
