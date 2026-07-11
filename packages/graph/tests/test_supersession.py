"""DB-backed tests for the bitemporal cascade and point-in-time queries.

Skipped unless TEST_DATABASE_URL is set (see conftest). They verify that
superseding a regulation closes the validity of everything that hangs off it —
requirements, obligations, gaps — and that an "as of" filter reconstructs the
state correctly for dates before and after the cut.
"""

from __future__ import annotations

from datetime import date

import pytest
from policyai_graph.graph_ops import supersede_node
from policyai_graph.models import Node, NodeType
from policyai_graph.models_app import (
    Gap,
    GapStatus,
    Obligation,
    ObligationStatus,
    Requirement,
)
from policyai_graph.temporal import app_valid_as_of, is_valid_as_of, node_valid_as_of
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

OLD_EFF = date(2026, 1, 1)
NEW_EFF = date(2026, 6, 1)


async def _seed_regulation_with_state(
    session: AsyncSession,
) -> tuple[Node, Obligation, Requirement, Gap]:
    old = Node(
        node_type=NodeType.REGULATION.value,
        properties={"canonical_key": "rbi.circ.old", "title": "Old Circular"},
        effective_from=OLD_EFF,
        is_current=True,
    )
    session.add(old)
    await session.flush()

    req = Requirement(
        regulation_node_id=old.id, text="File a quarterly return", seq=0, effective_date=OLD_EFF
    )
    ob = Obligation(
        org_id=None,
        regulation_node_id=old.id,
        title="Quarterly return",
        summary="must file",
        status=ObligationStatus.OPEN.value,
        effective_date=OLD_EFF,
    )
    session.add_all([req, ob])
    await session.flush()

    gap = Gap(
        org_id=None,
        obligation_id=ob.id,
        requirement_id=req.id,
        description="No filing process",
        status=GapStatus.OPEN.value,
        effective_date=OLD_EFF,
    )
    session.add(gap)
    await session.flush()
    return old, ob, req, gap


@pytest.mark.asyncio
async def test_supersession_cascades_to_requirements(session: AsyncSession) -> None:
    old, ob, req, gap = await _seed_regulation_with_state(session)
    new = Node(
        node_type=NodeType.REGULATION.value,
        properties={"canonical_key": "rbi.circ.new", "title": "New Circular"},
        effective_from=NEW_EFF,
        is_current=True,
    )
    session.add(new)
    await session.flush()

    acted = await supersede_node(session, old=old, new=new)
    assert acted
    await session.commit()

    for obj in (old, ob, req, gap):
        await session.refresh(obj)

    # node retired as of the new regulation's effective date
    assert old.is_current is False
    assert old.effective_to == NEW_EFF
    assert old.superseded_by_node_id == new.id
    # obligation + gap closed
    assert ob.status == ObligationStatus.SUPERSEDED.value
    assert ob.valid_to == NEW_EFF and ob.invalidated_at is not None
    assert gap.status == GapStatus.CLOSED.value and gap.valid_to == NEW_EFF
    # NEW: the requirement is no longer orphaned — its validity is closed too
    assert req.valid_to == NEW_EFF and req.invalidated_at is not None


@pytest.mark.asyncio
async def test_supersession_is_idempotent(session: AsyncSession) -> None:
    old, *_ = await _seed_regulation_with_state(session)
    new = Node(
        node_type=NodeType.REGULATION.value,
        properties={"canonical_key": "rbi.circ.new2"},
        effective_from=NEW_EFF,
        is_current=True,
    )
    session.add(new)
    await session.flush()
    assert await supersede_node(session, old=old, new=new) is True
    # second call is a no-op (already retired)
    assert await supersede_node(session, old=old, new=new) is False


@pytest.mark.asyncio
async def test_as_of_filters_select_point_in_time_state(session: AsyncSession) -> None:
    old, ob, req, gap = await _seed_regulation_with_state(session)
    new = Node(
        node_type=NodeType.REGULATION.value,
        properties={"canonical_key": "rbi.circ.new3", "title": "New Circular"},
        effective_from=NEW_EFF,
        is_current=True,
    )
    session.add(new)
    await session.flush()
    await supersede_node(session, old=old, new=new)
    await session.commit()

    # Before the cut: the old regulation IS in force.
    before = date(2026, 3, 1)
    reg_ids_before = set(
        (
            await session.execute(
                select(Node.id).where(
                    Node.node_type == NodeType.REGULATION.value, node_valid_as_of(Node, before)
                )
            )
        )
        .scalars()
        .all()
    )
    assert old.id in reg_ids_before and new.id not in reg_ids_before

    # After the cut: the old regulation is out, the new one is in.
    after = date(2026, 9, 1)
    reg_ids_after = set(
        (
            await session.execute(
                select(Node.id).where(
                    Node.node_type == NodeType.REGULATION.value, node_valid_as_of(Node, after)
                )
            )
        )
        .scalars()
        .all()
    )
    assert new.id in reg_ids_after and old.id not in reg_ids_after

    # Obligation valid-time tracks the same boundary.
    ob_before = (
        (await session.execute(select(Obligation).where(app_valid_as_of(Obligation, before))))
        .scalars()
        .all()
    )
    ob_after = (
        (await session.execute(select(Obligation).where(app_valid_as_of(Obligation, after))))
        .scalars()
        .all()
    )
    assert ob.id in {o.id for o in ob_before}
    assert ob.id not in {o.id for o in ob_after}


def test_is_valid_as_of_matches_sql_boundary() -> None:
    # Pure cross-check of the half-open boundary the SQL relies on.
    assert is_valid_as_of(OLD_EFF, NEW_EFF, date(2026, 3, 1))
    assert not is_valid_as_of(OLD_EFF, NEW_EFF, NEW_EFF)
    assert not is_valid_as_of(OLD_EFF, NEW_EFF, date(2026, 9, 1))
