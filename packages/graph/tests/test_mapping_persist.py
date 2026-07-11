"""DB-backed tests for the mapping engine's persistence behaviour.

The LLM call is stubbed (we are testing the write path, not the model), so these
verify the parts that bit real users: a re-map must not wipe human task progress,
must not spam duplicate NEW_OBLIGATION alerts, and must never persist an
ungrounded (hallucinated) requirement gap. Skipped unless TEST_DATABASE_URL is set.
"""

from __future__ import annotations

from datetime import date

import pytest
from policyai_extraction.mapping import map_obligation
from policyai_extraction.schemas import MappedTask, ObligationMapping, RequirementGap
from policyai_graph.models import Edge, EdgeType, Node, NodeType
from policyai_graph.models_app import (
    DEFAULT_ORG_ID,
    Alert,
    CompanyProfile,
    Gap,
    Requirement,
    Task,
    TaskStatus,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class _FakeLLM:
    """Stand-in for LLMClient.extract returning a fixed mapping."""

    def __init__(self, mapping: ObligationMapping) -> None:
        self._mapping = mapping
        self.calls = 0

    async def extract(self, *args, **kwargs):
        self.calls += 1
        return self._mapping


async def _seed(session: AsyncSession) -> Node:
    ec = Node(node_type=NodeType.ENTITY_CLASS.value, properties={"canonical_key": "nbfc_mfi"})
    reg = Node(
        node_type=NodeType.REGULATION.value,
        properties={
            "canonical_key": "rbi.circ.x",
            "title": "MFI Pricing Circular",
            "summary": "pricing rules",
            "regulator": "rbi",
            "document_type": "circular",
        },
        effective_from=date(2026, 1, 1),
        is_current=True,
    )
    session.add_all([ec, reg])
    await session.flush()
    session.add(Edge(source_id=reg.id, target_id=ec.id, edge_type=EdgeType.APPLIES_TO.value))
    session.add(
        Requirement(
            regulation_node_id=reg.id,
            text="Disclose the effective interest rate in the loan factsheet.",
            seq=0,
        )
    )
    session.add(
        CompanyProfile(
            org_id=DEFAULT_ORG_ID,
            entity_classes=["nbfc_mfi"],
            topics=[],
            regulators=["rbi"],
            notes="Demo MFI",
        )
    )
    await session.flush()
    return reg


def _mapping() -> ObligationMapping:
    return ObligationMapping(
        is_relevant=True,
        confidence=0.8,
        title="Disclose effective interest rate",
        summary="Must disclose the effective interest rate.",
        severity="high",
        tasks=[MappedTask(title="Update factsheet"), MappedTask(title="Board sign-off")],
        requirement_gaps=[
            RequirementGap(
                requirement_index=0,
                status="gap",
                gap_description="Factsheet omits the effective interest rate disclosure.",
            )
        ],
    )


@pytest.mark.asyncio
async def test_remap_preserves_done_tasks_and_dedupes_alert(session: AsyncSession) -> None:
    reg = await _seed(session)
    llm = _FakeLLM(_mapping())

    ob = await map_obligation(session, reg.id, llm, org_id=DEFAULT_ORG_ID)
    await session.commit()
    assert ob is not None

    tasks = (await session.execute(select(Task).where(Task.obligation_id == ob.id))).scalars().all()
    assert len(tasks) == 2
    # A human completes one task.
    done = next(t for t in tasks if t.title == "Update factsheet")
    done.status = TaskStatus.DONE.value
    await session.commit()

    # Re-map the same regulation.
    await map_obligation(session, reg.id, llm, org_id=DEFAULT_ORG_ID)
    await session.commit()

    tasks2 = (
        (await session.execute(select(Task).where(Task.obligation_id == ob.id))).scalars().all()
    )
    # The completed task survived (not wiped), and is not duplicated.
    done_titles = [t.title for t in tasks2 if t.status == TaskStatus.DONE.value]
    assert done_titles.count("Update factsheet") == 1
    assert sum(1 for t in tasks2 if t.title == "Update factsheet") == 1

    # Only one NEW_OBLIGATION alert despite two maps.
    alert_count = (await session.execute(select(func.count()).select_from(Alert))).scalar_one()
    assert alert_count == 1


@pytest.mark.asyncio
async def test_ungrounded_gap_is_replaced_with_grounded_text(session: AsyncSession) -> None:
    reg = await _seed(session)
    m = _mapping()
    # Hallucinated gap text that shares nothing with the requirement.
    m.requirement_gaps = [
        RequirementGap(
            requirement_index=0,
            status="gap",
            gap_description="No cryptocurrency custody desk for offshore settlement.",
        )
    ]
    ob = await map_obligation(session, reg.id, _FakeLLM(m), org_id=DEFAULT_ORG_ID)
    await session.commit()
    assert ob is not None

    gap = (
        await session.execute(
            select(Gap).where(Gap.obligation_id == ob.id, Gap.requirement_id.isnot(None))
        )
    ).scalar_one()
    # The hallucinated text was rejected and replaced with the requirement-derived one.
    assert "cryptocurrency" not in gap.description
    assert "interest rate" in gap.description
