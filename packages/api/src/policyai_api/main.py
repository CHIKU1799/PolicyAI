"""PolicyAI worker — FastAPI app (Render).

Handles the heavy/privileged operations the Vercel frontend can't: KB document
processing, profile derivation, obligation mapping, and graph-subgraph assembly.
Everything else (dashboard reads, task updates, the realtime alert feed) the
frontend does directly against Supabase.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from policyai_api.deps import get_session
from policyai_api.routes import ask, documents, graph, internal, profile, scan

app = FastAPI(title="PolicyAI Worker", version="0.1.0")

_origins = [o.strip() for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(profile.router)
app.include_router(internal.router)
app.include_router(graph.router)
app.include_router(scan.router)
app.include_router(ask.router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness — the process is up. Cheap, no dependencies (Render healthcheck)."""
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    """Readiness — the worker can actually reach the database. Returns 503 with a
    reason when the DB is unreachable, so monitoring means something."""
    agen = get_session()
    session = await agen.__anext__()
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok", "db": "ok"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"status": "degraded", "db": "error", "detail": str(exc)[:200]}, status_code=503
        )
    finally:
        await agen.aclose()
