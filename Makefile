ifneq (,$(wildcard .env))
    include .env
    export
endif

.PHONY: help install test lint format db-up db-down db-reset db-migrate db-seed \
        dev-api dev-web crawl eval eval-offline eval-baseline ingest \
        export-graph backup

help:
	@echo "PolicyAI — available targets:"
	@echo "  install    Install Python workspace dependencies via uv"
	@echo "  test       Run pytest across all packages"
	@echo "  lint       Run ruff + black --check"
	@echo "  format     Auto-fix with ruff and black"
	@echo "  db-migrate Apply Alembic migrations (uses DATABASE_URL -> Supabase)"
	@echo "  db-seed    Insert regulators, entity classes, acts, monitoring sources"
	@echo "  seed-demo  Insert a demo regulation + profile + obligation + tasks"
	@echo "  crawl      Run one monitoring pass over all enabled sources"
	@echo "  eval          Run full eval suite (mapping offline + extraction live), gate on regressions"
	@echo "  eval-offline  Run only the offline mapping-quality suite (no API key needed)"
	@echo "  eval-baseline Promote the latest results to the committed regression baseline"
	@echo "  ingest        Ingest pre-fetched docs (FILE=path.jsonl) through the extraction pipeline"
	@echo "  export-graph  Portable JSON backup of the whole compliance graph (OUT=path optional)"
	@echo "  backup        Native pg_dump backup -> backups/db-<ts>.sql.gz"
	@echo "  dev-api    Run the FastAPI worker locally (port 8000)"
	@echo "  dev-web    Run the Next.js frontend locally (port 3000)"
	@echo ""
	@echo "  Cloud DB targets (optional local Postgres):"
	@echo "  db-up/db-down/db-reset   docker compose Postgres for offline dev"
	@echo ""
	@echo "  First-time Supabase setup: run supabase/migrations/0000_platform.sql"
	@echo "  in the SQL editor, then 'make db-migrate db-seed'."

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run black --check .

format:
	uv run ruff check --fix .
	uv run black .

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d postgres

db-migrate:
	cd packages/graph && uv run alembic upgrade head

db-seed:
	uv run python -m policyai_graph.seed

seed-demo:
	uv run python -m policyai_graph.seed_demo

crawl:
	uv run python -m policyai_scrapers.runner

ingest:
	uv run python -m policyai_extraction.ingest $(FILE) $(ARGS)

ingest-policies:
	uv run python -m policyai_extraction.ingest_policies $(DIR) $(ARGS)

export-graph:
	uv run python -m policyai_graph.backup $(OUT)

backup:
	bash scripts/backup_db.sh

map:
	uv run python -m policyai_extraction.map_all

eval:
	uv run python -m policyai_extraction.eval.run_eval

eval-offline:
	uv run python -m policyai_extraction.eval.run_eval --only mapping

eval-baseline:
	uv run python -m policyai_extraction.eval.run_eval --promote

storage-check:
	uv run python -m policyai_extraction.storage_check

dev-api:
	uv run uvicorn policyai_api.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	cd frontend && npm run dev
