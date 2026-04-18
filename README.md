# PolicyAI

Regulatory intelligence platform for India — ingests RBI and SEBI circulars,
extracts structured information using the Claude API, and exposes a queryable
knowledge graph via FastAPI + a Next.js frontend.

See [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) for the full spec: scope,
success criteria, non-goals, and the graph schema.

## Layout

```
policyai/
├── docker-compose.yml        # Postgres 15 + pgvector
├── pyproject.toml            # uv workspace root
├── Makefile                  # install / test / lint / db-* targets
├── .env.example              # copy to .env before running
├── scripts/init-db.sql       # CREATE EXTENSION vector
├── packages/
│   ├── scrapers/             # Playwright scrapers for RBI + SEBI
│   ├── extraction/           # Claude-powered structured extraction
│   ├── graph/                # SQLAlchemy 2.0 async + Alembic + pgvector
│   └── api/                  # FastAPI service
└── frontend/                 # Next.js 14 app router + Tailwind
```

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for Python deps
- Node.js 20+ and npm (for the frontend)
- Docker (for local Postgres + pgvector). On macOS without Docker Desktop:
  `brew install colima docker docker-compose && colima start`

## Quickstart

```bash
cp .env.example .env              # fill in ANTHROPIC_API_KEY
make install                      # uv sync — installs all 4 workspace packages
make db-up                        # start Postgres + pgvector
make db-migrate                   # apply Alembic migrations
make db-seed                      # insert regulators, entity classes, parent acts
make test                         # run integration tests (needs TEST_DATABASE_URL)
```

Frontend:

```bash
cd frontend
npm install
npm run dev                       # http://localhost:3000
```

## Makefile targets

| Target       | What it does |
|--------------|-----------------------------------------------------|
| `install`    | `uv sync` — install Python workspace |
| `test`       | `uv run pytest` across all packages |
| `lint`       | `ruff check` + `black --check` |
| `format`     | Auto-fix with `ruff --fix` and `black` |
| `db-up`      | Start Postgres (pgvector) via docker compose |
| `db-down`    | Stop Postgres, keep volume |
| `db-reset`   | Destroy volume and start fresh |
| `db-migrate` | `alembic upgrade head` |
| `db-seed`    | Insert canonical graph seed data |

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

## Status

MVP in progress — see `PROJECT_CONTEXT.md` for the 2-week scope and
non-goals. Current milestone: knowledge graph schema + seed complete;
scraping and extraction pipelines next.
