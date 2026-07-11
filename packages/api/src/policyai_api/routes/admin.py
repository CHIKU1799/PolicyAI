"""Platform admin console API.

Cross-org visibility for PolicyAI operators: list every firm (org) on the platform
with headline counts, plus platform-wide totals. Guarded by ``require_platform_admin``
so only seeded platform super-admins can read it. Runs on the worker's DB session,
which uses the service-role connection and sees all orgs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, require_platform_admin
from policyai_api.deps import get_session

router = APIRouter(prefix="/admin", tags=["admin"])


class OrgRow(BaseModel):
    id: str
    name: str
    slug: str | None
    created_at: str | None
    members: int
    documents: int
    obligations: int
    gaps: int
    tasks: int


class AdminOverview(BaseModel):
    orgs: int
    users: int
    documents: int
    obligations: int
    gaps: int
    org_list: list[OrgRow]


async def _counts_by_org(session: AsyncSession, table: str) -> dict[str, int]:
    rows = await session.execute(
        text(
            f"select org_id::text, count(*) from public.{table} where org_id is not null "
            "group by org_id"
        )
    )
    return {oid: n for oid, n in rows.all()}


@router.get("/overview", response_model=AdminOverview)
async def overview(
    _admin: Principal = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminOverview:
    members = await _counts_by_org(session, "memberships")
    docs = await _counts_by_org(session, "company_documents")
    obligations = await _counts_by_org(session, "obligations")
    gaps = await _counts_by_org(session, "gaps")
    tasks = await _counts_by_org(session, "tasks")

    org_rows = await session.execute(
        text(
            "select id::text, name, slug, created_at::text from public.organizations "
            "order by created_at asc"
        )
    )
    org_list: list[OrgRow] = []
    for oid, name, slug, created_at in org_rows.all():
        org_list.append(
            OrgRow(
                id=oid,
                name=name,
                slug=slug,
                created_at=created_at,
                members=members.get(oid, 0),
                documents=docs.get(oid, 0),
                obligations=obligations.get(oid, 0),
                gaps=gaps.get(oid, 0),
                tasks=tasks.get(oid, 0),
            )
        )

    total_users = (
        await session.execute(text("select count(distinct user_id) from public.memberships"))
    ).scalar_one()
    return AdminOverview(
        orgs=len(org_list),
        users=int(total_users or 0),
        documents=sum(docs.values()),
        obligations=sum(obligations.values()),
        gaps=sum(gaps.values()),
        org_list=org_list,
    )
