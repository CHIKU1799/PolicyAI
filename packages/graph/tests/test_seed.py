from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.models import Edge, EdgeType, Node, NodeType
from policyai_graph.seed import ENTITY_CLASSES, PARENT_ACTS, REGULATORS, seed


@pytest.mark.asyncio
async def test_seed_inserts_expected_counts(session: AsyncSession) -> None:
    counts = await seed(session)
    expected_regulators = sum(1 + len(r["departments"]) for r in REGULATORS)
    assert counts[NodeType.REGULATOR.value] == expected_regulators
    assert counts[NodeType.ENTITY_CLASS.value] == len(ENTITY_CLASSES) == 20
    assert counts[NodeType.PARENT_ACT.value] == len(PARENT_ACTS) == 5


@pytest.mark.asyncio
async def test_seed_is_idempotent(session: AsyncSession) -> None:
    first = await seed(session)
    second = await seed(session)
    assert first == second


@pytest.mark.asyncio
async def test_regulator_departments_linked_to_parent(session: AsyncSession) -> None:
    await seed(session)

    rbi = (
        await session.execute(
            select(Node).where(
                Node.node_type == NodeType.REGULATOR.value,
                Node.properties["canonical_key"].astext == "rbi",
            )
        )
    ).scalar_one()

    dept_edges = (
        await session.execute(
            select(Edge).where(
                Edge.target_id == rbi.id, Edge.edge_type == EdgeType.ISSUED_BY.value
            )
        )
    ).scalars().all()

    rbi_dept_count = sum(1 for r in REGULATORS if r["canonical_key"] == "rbi") * len(
        next(r["departments"] for r in REGULATORS if r["canonical_key"] == "rbi")
    )
    entity_class_rbi_count = sum(1 for ec in ENTITY_CLASSES if ec["regulator"] == "rbi")
    assert len(dept_edges) == rbi_dept_count + entity_class_rbi_count


@pytest.mark.asyncio
async def test_parent_acts_linked_to_regulators(session: AsyncSession) -> None:
    await seed(session)

    rbi_act = (
        await session.execute(
            select(Node).where(
                Node.node_type == NodeType.PARENT_ACT.value,
                Node.properties["canonical_key"].astext == "rbi_act_1934",
            )
        )
    ).scalar_one()
    rbi = (
        await session.execute(
            select(Node).where(
                Node.node_type == NodeType.REGULATOR.value,
                Node.properties["canonical_key"].astext == "rbi",
            )
        )
    ).scalar_one()

    edge = (
        await session.execute(
            select(Edge).where(
                Edge.source_id == rbi.id,
                Edge.target_id == rbi_act.id,
                Edge.edge_type == EdgeType.DERIVED_FROM.value,
            )
        )
    ).scalar_one()
    assert edge is not None
