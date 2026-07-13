"""Daily digest — a ranked summary of the last 24h, emailed when Resend is
configured and always available as JSON via ``POST /internal/digest``.

Contents: new regulations (ranked by severity), new gaps, new alerts, and the
current overdue-task count. Deliberately org-scoped the same way the dashboard
is (DEFAULT_ORG for gaps/tasks; regulations are shared corpus-wide).

Run ad hoc / from cron:  uv run python -m policyai_extraction.digest [--hours 24]
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from policyai_graph.models import Node, NodeType
from policyai_graph.models_app import DEFAULT_ORG_ID, Alert, Gap, GapStatus, Task, TaskStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction.notifications import is_configured, send_email

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


async def build_digest(
    session: AsyncSession, *, org_id: UUID = DEFAULT_ORG_ID, hours: int = 24
) -> dict:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    regs = (
        (
            await session.execute(
                select(Node).where(
                    Node.node_type == NodeType.REGULATION.value, Node.created_at >= cutoff
                )
            )
        )
        .scalars()
        .all()
    )
    reg_items = sorted(
        (
            {
                "title": (n.properties or {}).get("title") or "?",
                "regulator": (n.properties or {}).get("regulator"),
                "severity": (n.properties or {}).get("severity") or "medium",
                "source_url": (n.properties or {}).get("source_url"),
            }
            for n in regs
        ),
        key=lambda r: _SEV_ORDER.get(r["severity"], 9),
    )

    new_gaps = (
        await session.execute(
            select(Gap.severity, func.count())
            .where(Gap.org_id == org_id, Gap.created_at >= cutoff)
            .group_by(Gap.severity)
        )
    ).all()
    overdue_tasks = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.org_id == org_id,
                    Task.due_date.isnot(None),
                    Task.due_date < datetime.now(UTC).date(),
                    Task.status != TaskStatus.DONE.value,
                )
            )
        ).scalar()
        or 0
    )
    open_gaps = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Gap)
                .where(Gap.org_id == org_id, Gap.status != GapStatus.CLOSED.value)
            )
        ).scalar()
        or 0
    )
    new_alerts = (
        await session.execute(
            select(Alert.kind, func.count()).where(Alert.created_at >= cutoff).group_by(Alert.kind)
        )
    ).all()

    return {
        "window_hours": hours,
        "generated_at": datetime.now(UTC).isoformat(),
        "new_regulations": reg_items,
        "new_gaps_by_severity": {s: c for s, c in new_gaps},
        "new_alerts_by_kind": {k: c for k, c in new_alerts},
        "overdue_tasks": overdue_tasks,
        "open_gaps": open_gaps,
    }


def render_digest_html(d: dict) -> str:
    regs = d["new_regulations"]
    reg_rows = "".join(
        f"<li><b>[{r['severity']}]</b> {r['title']}"
        + (f" <a href='{r['source_url']}'>source</a>" if r.get("source_url") else "")
        + "</li>"
        for r in regs[:15]
    )
    more = f"<p>…and {len(regs) - 15} more.</p>" if len(regs) > 15 else ""
    gaps = ", ".join(f"{c} {s}" for s, c in d["new_gaps_by_severity"].items()) or "none"
    alerts = ", ".join(f"{c} {k}" for k, c in d["new_alerts_by_kind"].items()) or "none"
    return (
        f"<h2>PolicyAI daily digest</h2>"
        f"<p><b>{len(regs)}</b> new regulation(s) in the last {d['window_hours']}h.</p>"
        f"<ul>{reg_rows}</ul>{more}"
        f"<p>New gaps: {gaps}. New alerts: {alerts}.</p>"
        f"<p>Currently open: <b>{d['open_gaps']}</b> gaps, "
        f"<b>{d['overdue_tasks']}</b> overdue tasks.</p>"
    )


async def send_digest(session: AsyncSession, *, hours: int = 24) -> dict:
    """Build the digest and email it when Resend is configured. Returns the
    digest dict with an added ``emailed`` flag either way."""
    d = await build_digest(session, hours=hours)
    emailed = False
    if is_configured():
        n = len(d["new_regulations"])
        emailed = await send_email(
            f"PolicyAI digest: {n} new regulation{'s' if n != 1 else ''}, "
            f"{d['overdue_tasks']} overdue tasks",
            render_digest_html(d),
        )
    d["emailed"] = emailed
    return d


def _main() -> None:
    import argparse
    import asyncio
    import json

    from policyai_graph.db import make_engine, make_sessionmaker

    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    args = ap.parse_args()

    async def run() -> None:
        engine = make_engine()
        async with make_sessionmaker(engine)() as session:
            d = await send_digest(session, hours=args.hours)
        await engine.dispose()
        print(json.dumps(d, indent=2, default=str))

    asyncio.run(run())


if __name__ == "__main__":
    _main()
