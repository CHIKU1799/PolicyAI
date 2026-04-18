ifneq (,$(wildcard .env))
    include .env
    export
endif

.PHONY: help install test lint format db-up db-down db-reset db-migrate db-seed

help:
	@echo "PolicyAI — available targets:"
	@echo "  install    Install Python workspace dependencies via uv"
	@echo "  test       Run pytest across all packages"
	@echo "  lint       Run ruff + black --check"
	@echo "  format     Auto-fix with ruff and black"
	@echo "  db-up      Start Postgres (pgvector) via docker compose"
	@echo "  db-down    Stop Postgres (keep volume)"
	@echo "  db-reset   Destroy Postgres volume and start fresh"
	@echo "  db-migrate Apply Alembic migrations (uses DATABASE_URL)"
	@echo "  db-seed    Insert canonical regulators, entity classes, parent acts"

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
