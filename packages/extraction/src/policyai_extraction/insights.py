"""Actionable insights — one canonical, prioritized computation of "what needs
attention", reused by the dashboard, the /insights API, and the Ask agent.

Each insight has a severity, a count, a plain-English description, and a concrete
next action (where to go). They are sorted by a priority score so the most
consequential, most numerous problems lead. This is deliberately server-side so
every surface agrees on the numbers and can read tables (nodes, requirements) the
browser can't.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from policyai_graph.models import Node, NodeType
from policyai_graph.models_app import (
    DEFAULT_ORG_ID,
    Control,
    Effectiveness,
    Gap,
    GapStatus,
    Obligation,
    ObligationControl,
    ObligationStatus,
    Requirement,
    Severity,
    Task,
    TaskStatus,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ACTIVE_OB = (ObligationStatus.OPEN.value, ObligationStatus.IN_REVIEW.value)
_WEIGHT = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.5}


async def _count(session: AsyncSession, stmt) -> int:
    return int((await session.execute(stmt)).scalar() or 0)


async def compute_insights(session: AsyncSession, org_id: UUID = DEFAULT_ORG_ID) -> dict:
    """Return {generated_at, posture_note, insights:[...]} for one org."""
    today = date.today()
    mapped_reg = select(Obligation.regulation_node_id).where(Obligation.org_id == org_id)
    covered_ob = select(ObligationControl.obligation_id)
    with_tasks = select(Task.obligation_id).where(Task.org_id == org_id)

    # Coverage funnel ---------------------------------------------------------
    unmapped_regs = await _count(
        session,
        select(func.count())
        .select_from(Node)
        .where(
            Node.node_type == NodeType.REGULATION.value,
            Node.is_current.is_(True),
            Node.id.notin_(mapped_reg),
        ),
    )
    uncovered_obl_regs = select(Obligation.regulation_node_id).where(
        Obligation.org_id == org_id,
        Obligation.status.in_(ACTIVE_OB),
        Obligation.id.notin_(covered_ob),
    )
    uncovered_requirements = await _count(
        session,
        select(func.count(Requirement.id)).where(
            Requirement.regulation_node_id.in_(uncovered_obl_regs)
        ),
    )
    obligations_no_control = await _count(
        session,
        select(func.count())
        .select_from(Obligation)
        .where(
            Obligation.org_id == org_id,
            Obligation.status.in_(ACTIVE_OB),
            Obligation.id.notin_(covered_ob),
        ),
    )

    # Trust / triage ----------------------------------------------------------
    low_confidence = await _count(
        session,
        select(func.count())
        .select_from(Obligation)
        .where(
            Obligation.org_id == org_id,
            Obligation.status.in_(ACTIVE_OB),
            Obligation.mapping_confidence.isnot(None),
            Obligation.mapping_confidence < 0.5,
        ),
    )
    high_sev_no_task = await _count(
        session,
        select(func.count())
        .select_from(Obligation)
        .where(
            Obligation.org_id == org_id,
            Obligation.status.in_(ACTIVE_OB),
            Obligation.severity.in_((Severity.CRITICAL.value, Severity.HIGH.value)),
            Obligation.id.notin_(with_tasks),
        ),
    )
    in_review = await _count(
        session,
        select(func.count())
        .select_from(Obligation)
        .where(Obligation.org_id == org_id, Obligation.status == ObligationStatus.IN_REVIEW.value),
    )

    # Remediation / controls --------------------------------------------------
    overdue_gaps = await _count(
        session,
        select(func.count())
        .select_from(Gap)
        .where(
            Gap.org_id == org_id,
            Gap.due_date.isnot(None),
            Gap.due_date < today,
            Gap.status != GapStatus.CLOSED.value,
        ),
    )
    open_requirement_gaps = await _count(
        session,
        select(func.count())
        .select_from(Gap)
        .where(
            Gap.org_id == org_id,
            Gap.requirement_id.isnot(None),
            Gap.status != GapStatus.CLOSED.value,
        ),
    )
    # Policy conflicts — the firm's own policy contradicts a regulation. A live
    # violation and the sharpest penalty exposure, so it leads the insight list.
    policy_conflicts = await _count(
        session,
        select(func.count())
        .select_from(Gap)
        .where(
            Gap.org_id == org_id,
            Gap.coverage_status == CoverageStatus.CONFLICTING.value,
            Gap.status != GapStatus.CLOSED.value,
        ),
    )
    ineffective_controls = await _count(
        session,
        select(func.count())
        .select_from(Control)
        .where(Control.org_id == org_id, Control.effectiveness == Effectiveness.INEFFECTIVE.value),
    )
    untested_controls = await _count(
        session,
        select(func.count())
        .select_from(Control)
        .where(Control.org_id == org_id, Control.effectiveness == Effectiveness.UNTESTED.value),
    )
    overdue_tasks = await _count(
        session,
        select(func.count())
        .select_from(Task)
        .where(
            Task.org_id == org_id,
            Task.due_date.isnot(None),
            Task.due_date < today,
            Task.status != TaskStatus.DONE.value,
        ),
    )
    stale_superseded_tasks = await _count(
        session,
        select(func.count())
        .select_from(Task)
        .join(Obligation, Obligation.id == Task.obligation_id)
        .where(
            Task.org_id == org_id,
            Task.status != TaskStatus.DONE.value,
            Obligation.status == ObligationStatus.SUPERSEDED.value,
        ),
    )

    catalog = [
        dict(
            key="overdue_gaps",
            count=overdue_gaps,
            severity="critical",
            label="Overdue gaps",
            description="Remediation gaps are past their due date.",
            action_label="Triage gaps",
            action_href="/gaps",
        ),
        dict(
            key="ineffective_controls",
            count=ineffective_controls,
            severity="critical",
            label="Ineffective controls",
            description="Controls tested ineffective — the obligations they cover are exposed.",
            action_label="Review controls",
            action_href="/controls",
        ),
        dict(
            key="high_sev_no_task",
            count=high_sev_no_task,
            severity="critical",
            label="High-severity obligations with no task",
            description="Critical/high obligations have no action assigned to anyone.",
            action_label="Open obligations",
            action_href="/obligations",
        ),
        dict(
            key="overdue_tasks",
            count=overdue_tasks,
            severity="high",
            label="Overdue tasks",
            description="Assigned compliance tasks are past their deadline.",
            action_label="Work the board",
            action_href="/tasks",
        ),
        dict(
            key="obligations_no_control",
            count=obligations_no_control,
            severity="high",
            label="Obligations with no control",
            description="Active obligations aren't linked to any control.",
            action_label="Map controls",
            action_href="/obligations",
        ),
        dict(
            key="open_requirement_gaps",
            count=open_requirement_gaps,
            severity="high",
            label="Open requirement gaps",
            description="Specific regulatory requirements your policies don't yet satisfy.",
            action_label="Close requirement gaps",
            action_href="/gaps",
        ),
        dict(
            key="uncovered_requirements",
            count=uncovered_requirements,
            severity="high",
            label="Uncovered requirements",
            description="Discrete regulatory requirements sit under obligations "
            "that have no control.",
            action_label="Review requirements",
            action_href="/obligations",
        ),
        dict(
            key="unmapped_regulations",
            count=unmapped_regs,
            severity="medium",
            label="Unmapped regulations",
            description="Ingested regulations haven't been assessed against your profile yet.",
            action_label="Run mapping",
            action_href="/obligations",
        ),
        dict(
            key="low_confidence",
            count=low_confidence,
            severity="medium",
            label="Low-confidence mappings",
            description="Obligations the engine is unsure apply to you — confirm or dismiss.",
            action_label="Verify obligations",
            action_href="/obligations",
        ),
        dict(
            key="untested_controls",
            count=untested_controls,
            severity="medium",
            label="Untested controls",
            description="Controls have never been tested, so effectiveness is unknown.",
            action_label="Schedule tests",
            action_href="/controls",
        ),
        dict(
            key="in_review",
            count=in_review,
            severity="low",
            label="Obligations in review",
            description="Obligations awaiting a reviewer's decision.",
            action_label="Continue review",
            action_href="/obligations",
        ),
        dict(
            key="stale_superseded_tasks",
            count=stale_superseded_tasks,
            severity="low",
            label="Stale tasks on superseded obligations",
            description="Open tasks belong to obligations whose regulation was "
            "superseded — likely closeable.",
            action_label="Clean up tasks",
            action_href="/tasks",
        ),
    ]
    insights = [i for i in catalog if i["count"] > 0]
    for i in insights:
        i["score"] = round(_WEIGHT[i["severity"]] * (1 + i["count"] ** 0.5), 3)
    insights.sort(key=lambda i: i["score"], reverse=True)

    if not insights:
        posture = "Nothing needs attention — every active obligation is covered and on track."
    else:
        top = insights[0]
        posture = (
            f"{len(insights)} areas need attention; "
            f"start with {top['label'].lower()} ({top['count']})."
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "posture_note": posture,
        "insights": insights,
    }
