# PolicyAI worker image: FastAPI API, crawler, and digest jobs all run from
# this one image (same layout as render.yaml). Python 3.12 + uv + Playwright
# Chromium for the RBI/SEBI/IRDAI scrapers.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    HF_HOME=/data/hf-cache

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Dependency layer first so code edits don't re-resolve the lockfile.
COPY pyproject.toml uv.lock ./
COPY packages ./packages
RUN uv sync --frozen --no-dev

# Chromium + system deps for the Playwright-based scrapers.
RUN uv run playwright install --with-deps chromium

COPY scripts ./scripts

EXPOSE 8000

# Local-embeddings model cache persists in /data (mount a volume).
VOLUME ["/data"]

CMD ["uv", "run", "uvicorn", "policyai_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
