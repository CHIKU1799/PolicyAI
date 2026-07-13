"""Manual 'Scan now' trigger for the dashboard.

Kicks off a full monitoring pass in the background (force=True ignores per-source
cadence) and returns immediately — the crawl + extraction can take minutes. New
regulations, obligations, and alerts stream into the UI via Supabase Realtime as
they land, so the caller doesn't need to poll this endpoint.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from policyai_extraction.map_all import map_unmapped
from policyai_scrapers.runner import run_once
from pydantic import BaseModel

from policyai_api.auth import Principal, effective_org, resolve_principal

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


class MapRequest(BaseModel):
    org_id: UUID | None = None  # honored only for platform admins
    limit: int = 1000


@router.post("/map", response_model=ScanResponse, status_code=202)
async def map_now(
    background: BackgroundTasks,
    req: MapRequest | None = None,
    principal: Principal = Depends(resolve_principal),
) -> ScanResponse:
    """Map every ingested regulation that still lacks an obligation for the
    caller's org. Useful after a bulk ingest or a new firm's first upload."""
    req = req or MapRequest()
    org_id = effective_org(principal, req.org_id)
    background.add_task(map_unmapped, org_id, min(req.limit, 1000))
    return ScanResponse(
        status="started",
        detail="Obligation mapping started for unmapped regulations. "
        "New obligations, gaps and tasks appear in the dashboard as they are produced.",
    )
