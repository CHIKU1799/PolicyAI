"""Manual 'Scan now' trigger for the dashboard.

Kicks off a full monitoring pass in the background (force=True ignores per-source
cadence) and returns immediately — the crawl + extraction can take minutes. New
regulations, obligations, and alerts stream into the UI via Supabase Realtime as
they land, so the caller doesn't need to poll this endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from policyai_scrapers.runner import run_once
from pydantic import BaseModel

router = APIRouter(tags=["scan"])


class ScanResponse(BaseModel):
    status: str
    detail: str


@router.post("/scan", response_model=ScanResponse, status_code=202)
async def scan_now(background: BackgroundTasks) -> ScanResponse:
    background.add_task(run_once, force=True)
    return ScanResponse(
        status="started",
        detail="Monitoring pass started for all enabled sources. "
        "Results appear in the dashboard as they are processed.",
    )
