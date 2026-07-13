"""Bitemporal timeline for a regulation node — the 'what changed when' view.

Returns the supersession lineage (oldest → newest), the obligations tied to the
node and their current validity, and the append-only audit events, so the UI can
show when a regulation/obligation came into or went out of force.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from policyai_graph.models import Node, NodeType
from policyai_graph.models_app import (
    AuditEvent,
    Gap,
    GapStatus,
    Obligation,
    Requirement,
)
from policyai_graph.temporal import app_valid_as_of, node_valid_as_of
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, effective_org, resolve_principal
from policyai_api.deps import get_session

router = APIRouter(prefix="/timeline", tags=["timeline"])


class TimelineNode(BaseModel):
    id: str
    title: str | None
    is_current: bool
    effective_from: str | None
    effective_to: str | None
    invalidated_at: str | None
    superseded_by_node_id: str | None


class TimelineObligation(BaseModel):
    id: str
    title: str
    status: str
    valid_to: str | None
    invalidated_at: str | None


class TimelineEvent(BaseModel):
    action: str
    entity_type: str
    detail: dict
    created_at: str


class TimelineRequirement(BaseModel):
    text: str
    requirement_type: str
    frequency: str | None
    citation: str | None
    evidence_expected: str | None
    penalty: str | None
    gap_status: str | None  # open/remediating/... if this requirement has a gap, else null
    gap_description: str | None


class TimelineResponse(BaseModel):
    node: TimelineNode
    chain: list[TimelineNode]
    obligations: list[TimelineObligation]
    requirements: list[TimelineRequirement]
    events: list[TimelineEvent]


def _to_node(n: Node) -> TimelineNode:
    p = n.properties or {}
    return TimelineNode(
        id=str(n.id),
        title=p.get("title") or p.get("name") or p.get("canonical_key"),
        is_current=n.is_current,
        effective_from=str(n.effective_from) if n.effective_from else None,
        effective_to=str(n.effective_to) if n.effective_to else None,
        invalidated_at=n.invalidated_at.isoformat() if n.invalidated_at else None,
        superseded_by_node_id=str(n.superseded_by_node_id) if n.superseded_by_node_id else None,
    )


class AsOfRegulation(BaseModel):
    id: str
    title: str | None
    effective_from: str | None
    effective_to: str | None
    is_current: bool


class AsOfObligation(BaseModel):
    id: str
    title: str
    status: str
    severity: str
    effective_date: str | None
    valid_to: str | None


class AsOfSnapshot(BaseModel):
    as_of: str
    regulations_in_force: int
    obligations_in_force: int
    regulations: list[AsOfRegulation]
    obligations: list[AsOfObligation]


@router.get("/as-of/{as_of}", response_model=AsOfSnapshot)
async def as_of_snapshot(
    as_of: date,
    org_id: UUID | None = None,
    principal: Principal = Depends(resolve_principal),
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
) -> AsOfSnapshot:
    """Point-in-time view: which regulations and obligations were in force on ``as_of``.

    This is the payoff of the bitemporal model — instead of only "current state",
    the dashboard can reconstruct the compliance posture as it stood on any past
    (or future-dated) day, by filtering on the valid-time interval rather than the
    ``is_current`` flag. Half-open intervals: a record ending on ``as_of`` is out.
    """
    org_id = effective_org(principal, org_id)
    reg_rows = (
        (
            await session.execute(
                select(Node)
                .where(
                    Node.node_type == NodeType.REGULATION.value,
                    node_valid_as_of(Node, as_of),
                )
                .order_by(Node.effective_from.desc().nullslast())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    ob_rows = (
        (
            await session.execute(
                select(Obligation)
                .where(
                    Obligation.org_id == org_id,
                    app_valid_as_of(Obligation, as_of),
                )
                .order_by(Obligation.effective_date.desc().nullslast())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    reg_count = (
        await session.execute(
            select(func.count())
            .select_from(Node)
            .where(
                Node.node_type == NodeType.REGULATION.value,
                node_valid_as_of(Node, as_of),
            )
        )
    ).scalar_one()
    ob_count = (
        await session.execute(
            select(func.count())
            .select_from(Obligation)
            .where(Obligation.org_id == org_id, app_valid_as_of(Obligation, as_of))
        )
    ).scalar_one()

    return AsOfSnapshot(
        as_of=str(as_of),
        regulations_in_force=reg_count,
        obligations_in_force=ob_count,
        regulations=[
            AsOfRegulation(
                id=str(n.id),
                title=(n.properties or {}).get("title") or (n.properties or {}).get("name"),
                effective_from=str(n.effective_from) if n.effective_from else None,
                effective_to=str(n.effective_to) if n.effective_to else None,
                is_current=n.is_current,
            )
            for n in reg_rows
        ],
        obligations=[
            AsOfObligation(
                id=str(o.id),
                title=o.title,
                status=o.status,
                severity=o.severity,
                effective_date=str(o.effective_date) if o.effective_date else None,
                valid_to=str(o.valid_to) if o.valid_to else None,
            )
            for o in ob_rows
        ],
    )


@router.get("/{node_id}", response_model=TimelineResponse)
async def timeline(
    node_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TimelineResponse:
    node = (await session.execute(select(Node).where(Node.id == node_id))).scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="node not found")

    # Walk backward to the oldest ancestor, then forward through supersessions —
    # producing the full lineage oldest -> newest.
    seen: set[UUID] = set()
    oldest = node
    while True:
        prev = (
            await session.execute(
                select(Node).where(Node.superseded_by_node_id == oldest.id).limit(1)
            )
        ).scalar_one_or_none()
        if prev is None or prev.id in seen:
            break
        seen.add(prev.id)
        oldest = prev

    chain: list[Node] = []
    cur: Node | None = oldest
    walked: set[UUID] = set()
    while cur is not None and cur.id not in walked:
        walked.add(cur.id)
        chain.append(cur)
        if cur.superseded_by_node_id is None:
            break
        cur = (
            await session.execute(select(Node).where(Node.id == cur.superseded_by_node_id))
        ).scalar_one_or_none()

    obligations = (
        (await session.execute(select(Obligation).where(Obligation.regulation_node_id == node_id)))
        .scalars()
        .all()
    )
    ob_ids = [o.id for o in obligations]

    requirements = (
        (
            await session.execute(
                select(Requirement)
                .where(Requirement.regulation_node_id == node_id)
                .order_by(Requirement.seq)
            )
        )
        .scalars()
        .all()
    )
    # Requirement-level gaps for these requirements (the concrete coverage map).
    req_ids = [r.id for r in requirements]
    gap_by_req: dict = {}
    if req_ids:
        gap_rows = (
            (await session.execute(select(Gap).where(Gap.requirement_id.in_(req_ids))))
            .scalars()
            .all()
        )
        for g in gap_rows:
            # Prefer an open gap if a requirement somehow has more than one.
            cur = gap_by_req.get(g.requirement_id)
            cur_closed = cur is not None and cur.status == GapStatus.CLOSED.value
            if cur is None or (cur_closed and g.status != GapStatus.CLOSED.value):
                gap_by_req[g.requirement_id] = g

    event_filter = [AuditEvent.entity_id == node_id]
    if ob_ids:
        event_filter.append(AuditEvent.entity_id.in_(ob_ids))
    events = (
        (
            await session.execute(
                select(AuditEvent).where(or_(*event_filter)).order_by(AuditEvent.created_at)
            )
        )
        .scalars()
        .all()
    )

    return TimelineResponse(
        node=_to_node(node),
        chain=[_to_node(n) for n in chain],
        obligations=[
            TimelineObligation(
                id=str(o.id),
                title=o.title,
                status=o.status,
                valid_to=str(o.valid_to) if o.valid_to else None,
                invalidated_at=o.invalidated_at.isoformat() if o.invalidated_at else None,
            )
            for o in obligations
        ],
        requirements=[
            TimelineRequirement(
                text=r.text,
                requirement_type=r.requirement_type,
                frequency=r.frequency,
                citation=r.citation,
                evidence_expected=r.evidence_expected,
                penalty=r.penalty,
                gap_status=gap_by_req[r.id].status if r.id in gap_by_req else None,
                gap_description=gap_by_req[r.id].description if r.id in gap_by_req else None,
            )
            for r in requirements
        ],
        events=[
            TimelineEvent(
                action=e.action,
                entity_type=e.entity_type,
                detail=e.detail or {},
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ],
    )
