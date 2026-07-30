"""Actionable-insights endpoint — the prioritized 'what needs attention' feed.

One canonical computation (``policyai_extraction.insights``) the dashboard and the
Ask agent both consume, so the numbers always agree.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from policyai_extraction.insights import compute_insights
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, effective_org, resolve_principal
from policyai_api.deps import get_session
from policyai_api.ttl_cache import ttl_cache

router = APIRouter(prefix="/insights", tags=["insights"])


class Insight(BaseModel):
    key: str
    label: str
    severity: str
    count: int
    description: str
    action_label: str
    action_href: str
    score: float


class Coverage(BaseModel):
    applicable: int
    covered: int
    uncovered: int
    pct: float | None


class InsightsResponse(BaseModel):
    generated_at: str
    posture_note: str
    coverage: Coverage
    insights: list[Insight]


# Insights aggregate several tables per request and the dashboard polls them;
# a 90s in-process cache absorbs that. Keyed by org id — tenants never share.
@ttl_cache(seconds=90, max_entries=512)
async def _cached_insights(org_id: UUID, session: AsyncSession) -> dict:
    return await compute_insights(session, org_id)


@router.get("", response_model=InsightsResponse)
async def insights(
    org_id: UUID | None = None,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
) -> InsightsResponse:
    # Org comes from the verified token; a client-supplied org_id is honored
    # only for platform admins (the operator console inspecting a firm).
    return InsightsResponse(**await _cached_insights(effective_org(principal, org_id), session))
