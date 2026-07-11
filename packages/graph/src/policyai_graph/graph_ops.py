"""Idempotent upsert helpers for the knowledge graph.

The single source of truth for "get-or-create this node / edge" used by both the
canonical seed (``seed.py``) and the live extraction pipeline. Dedup identity for
nodes is the ``canonical_key`` property; for edges it is the (source, target,
type) triple guarded by ``uq_edge_triple``.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.audit import record_event
from policyai_graph.models import Edge, EdgeType, Node, NodeType
from policyai_graph.models_app import (
    Gap,
    GapStatus,
    Obligation,
    ObligationStatus,
    Requirement,
)


async def find_node(
    session: AsyncSession, *, node_type: NodeType, canonical_key: str
) -> Node | None:
    stmt = select(Node).where(
        Node.node_type == node_type.value,
        Node.properties["canonical_key"].astext == canonical_key,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_or_create_node(
    session: AsyncSession,
    *,
    node_type: NodeType,
    canonical_key: str,
    properties: dict,
) -> Node:
    existing = await find_node(session, node_type=node_type, canonical_key=canonical_key)
    if existing is not None:
        return existing
    node = Node(node_type=node_type.value, properties=properties)
    session.add(node)
    await session.flush()
    return node


async def get_or_create_edge(
    session: AsyncSession,
    *,
    source: Node,
    target: Node,
    edge_type: EdgeType,
    properties: dict | None = None,
) -> Edge:
    stmt = select(Edge).where(
        Edge.source_id == source.id,
        Edge.target_id == target.id,
        Edge.edge_type == edge_type.value,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing
    edge = Edge(
        source_id=source.id,
        target_id=target.id,
        edge_type=edge_type.value,
        properties=properties or {},
    )
    session.add(edge)
    await session.flush()
    return edge


async def supersede_node(
    session: AsyncSession,
    *,
    old: Node,
    new: Node,
    as_of: date | None = None,
) -> bool:
    """Mark ``old`` as superseded by ``new`` and cascade to its compliance state.

    This is what gives the graph its time axis: when a new regulation supersedes or
    amends an existing one, the predecessor stops being current as of ``as_of`` (the
    new regulation's effective date), its obligations move to ``superseded`` and its
    open gaps close — each recorded as an append-only ``AuditEvent``. Idempotent: a
    node already retired is left untouched. Returns True if it acted. Caller commits.
    """
    if old.id == new.id or not old.is_current:
        return False
    cut = as_of or new.effective_from
    old.is_current = False
    old.effective_to = cut
    old.invalidated_at = func.now()
    old.superseded_by_node_id = new.id

    # Requirements are objective facts of the old regulation: close their validity
    # so a point-in-time query after `cut` never surfaces a requirement from a
    # superseded document (the orphaning bug bitemporal is meant to prevent).
    requirements = (
        (await session.execute(select(Requirement).where(Requirement.regulation_node_id == old.id)))
        .scalars()
        .all()
    )
    for req in requirements:
        if req.invalidated_at is not None:
            continue
        req.valid_to = cut
        req.invalidated_at = func.now()

    obligations = (
        (await session.execute(select(Obligation).where(Obligation.regulation_node_id == old.id)))
        .scalars()
        .all()
    )
    for ob in obligations:
        if ob.status == ObligationStatus.SUPERSEDED.value:
            continue
        ob.status = ObligationStatus.SUPERSEDED.value
        ob.valid_to = cut
        ob.invalidated_at = func.now()
        await record_event(
            session,
            org_id=ob.org_id,
            entity_type="obligation",
            entity_id=ob.id,
            action="obligation_invalidated",
            detail={"reason": "source_regulation_superseded", "superseded_by_node": str(new.id)},
        )
        gaps = (
            (await session.execute(select(Gap).where(Gap.obligation_id == ob.id))).scalars().all()
        )
        for g in gaps:
            if g.status == GapStatus.CLOSED.value:
                continue
            g.status = GapStatus.CLOSED.value
            g.valid_to = cut
            g.invalidated_at = func.now()

    await record_event(
        session,
        entity_type="node",
        entity_id=old.id,
        action="regulation_superseded",
        detail={
            "superseded_by": str(new.id),
            "old_title": (old.properties or {}).get("title"),
            "new_title": (new.properties or {}).get("title"),
            "effective_to": str(cut) if cut else None,
        },
    )
    return True
