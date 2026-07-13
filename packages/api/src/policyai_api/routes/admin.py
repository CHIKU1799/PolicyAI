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
    scans: int
    alerts: int
    regulations: int
    org_list: list[OrgRow]


async def _scalar(session: AsyncSession, sql: str) -> int:
    try:
        return int((await session.execute(text(sql))).scalar_one() or 0)
    except Exception:  # noqa: BLE001 - a missing table/type shouldn't 500 the console
        return 0


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

    total_users = await _scalar(session, "select count(distinct user_id) from public.memberships")
    scans = await _scalar(session, "select count(*) from public.scan_runs")
    alerts = await _scalar(session, "select count(*) from public.alerts")
    regulations = await _scalar(
        session, "select count(*) from public.nodes where node_type = 'regulation'"
    )
    return AdminOverview(
        orgs=len(org_list),
        users=total_users,
        documents=sum(docs.values()),
        obligations=sum(obligations.values()),
        gaps=sum(gaps.values()),
        scans=scans,
        alerts=alerts,
        regulations=regulations,
        org_list=org_list,
    )


class HealthCheck(BaseModel):
    name: str
    status: str  # ok | warn | fail
    detail: str


class SystemHealth(BaseModel):
    generated_at: str
    status: str  # worst of the checks
    checks: list[HealthCheck]


@router.get("/health", response_model=SystemHealth, dependencies=[Depends(require_platform_admin)])
async def system_health(session: AsyncSession = Depends(get_session)) -> SystemHealth:
    """Operator fault checks: is the machine that feeds every company healthy?"""
    from datetime import UTC, datetime, timedelta

    from policyai_extraction.llm import LLM_PROVIDER, OPENAI_BASE_URL, OPENAI_MODEL
    from policyai_graph.models import Node
    from policyai_graph.models_app import Alert, MonitoringSource, ScanRun
    from sqlalchemy import func, select
    from sqlalchemy import text as sqltext

    now = datetime.now(UTC)
    day_ago = now - timedelta(hours=24)
    checks: list[HealthCheck] = []

    def add(name: str, status: str, detail: str) -> None:
        checks.append(HealthCheck(name=name, status=status, detail=detail))

    # 1. Crawler freshness: every enabled source scanned within 2x its cadence.
    sources = (
        (await session.execute(select(MonitoringSource).where(MonitoringSource.enabled)))
        .scalars()
        .all()
    )
    stale = [
        s.name
        for s in sources
        if s.last_scanned_at is None
        or (now - s.last_scanned_at) > timedelta(hours=2 * (s.cadence_hours or 24))
    ]
    if not sources:
        add("Crawler sources", "fail", "No enabled monitoring sources.")
    elif stale:
        add(
            "Crawler sources",
            "warn",
            f"{len(stale)}/{len(sources)} enabled sources are stale: {', '.join(stale[:4])}",
        )
    else:
        add("Crawler sources", "ok", f"All {len(sources)} enabled sources scanned on cadence.")

    # 2. Scan failures in the last 24h.
    failed_scans = int(
        (
            await session.execute(
                select(func.count())
                .select_from(ScanRun)
                .where(ScanRun.started_at >= day_ago, ScanRun.status == "failed")
            )
        ).scalar()
        or 0
    )
    add(
        "Scan runs (24h)",
        "ok" if failed_scans == 0 else "warn",
        "No failed scans." if failed_scans == 0 else f"{failed_scans} failed scan run(s).",
    )

    # 3. Ingestion throughput: new regulations in the last 24h.
    new_regs = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Node)
                .where(Node.node_type == "regulation", Node.created_at >= day_ago)
            )
        ).scalar()
        or 0
    )
    add(
        "Ingestion (24h)",
        "ok" if new_regs > 0 else "warn",
        f"{new_regs} new regulation(s) extracted in the last 24h.",
    )

    # 4. Mapping backlog: regulations no org has an obligation for.
    unmapped = int(
        (
            await session.execute(
                sqltext(
                    "select count(*) from nodes n where n.node_type = 'regulation' "
                    "and not exists (select 1 from obligations o "
                    "where o.regulation_node_id = n.id)"
                )
            )
        ).scalar()
        or 0
    )
    total_regs = int(
        (
            await session.execute(
                select(func.count()).select_from(Node).where(Node.node_type == "regulation")
            )
        ).scalar()
        or 0
    )
    backlog_pct = round(100 * unmapped / total_regs, 1) if total_regs else 0.0
    add(
        "Obligation mapping backlog",
        "warn" if backlog_pct > 50 else "ok",
        f"{unmapped} of {total_regs} regulations ({backlog_pct}%) not yet mapped for any firm.",
    )

    # 5. Embedding coverage: raw documents missing an embedding can't be
    #    retrieved by the Copilot or the gap engine.
    no_embedding = int(
        (
            await session.execute(
                sqltext("select count(*) from raw_documents where embedding is null")
            )
        ).scalar()
        or 0
    )
    add(
        "Embeddings",
        "ok" if no_embedding == 0 else "warn",
        (
            "All documents embedded."
            if no_embedding == 0
            else f"{no_embedding} document(s) missing embeddings (retrieval-blind)."
        ),
    )

    # 6. Alert flow, with control failures called out.
    alerts_24h = int(
        (
            await session.execute(
                select(func.count()).select_from(Alert).where(Alert.created_at >= day_ago)
            )
        ).scalar()
        or 0
    )
    control_failures = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Alert)
                .where(Alert.created_at >= day_ago, Alert.kind == "control_failed")
            )
        ).scalar()
        or 0
    )
    add(
        "Alerts (24h)",
        "warn" if control_failures else "ok",
        f"{alerts_24h} alert(s); {control_failures} control failure(s).",
    )

    # 7. LLM provider wiring (config-level; live probes cost tokens).
    if LLM_PROVIDER == "anthropic":
        add("LLM provider", "ok", "Anthropic (extraction=sonnet, mapping=opus).")
    else:
        add("LLM provider", "ok", f"{OPENAI_BASE_URL} ({OPENAI_MODEL}).")

    worst = "ok"
    if any(c.status == "warn" for c in checks):
        worst = "warn"
    if any(c.status == "fail" for c in checks):
        worst = "fail"
    return SystemHealth(generated_at=now.isoformat(), status=worst, checks=checks)
