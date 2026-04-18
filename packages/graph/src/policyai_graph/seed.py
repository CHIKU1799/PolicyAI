"""Seed canonical graph data: regulators + sub-departments, entity classes, parent acts.

Idempotent: re-running will not duplicate rows. Uses the `canonical_key` property
on each node as the deduplication identity.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import Edge, EdgeType, Node, NodeType

REGULATORS: list[dict] = [
    {
        "canonical_key": "rbi",
        "name": "Reserve Bank of India",
        "short_name": "RBI",
        "kind": "central_bank",
        "departments": [
            {"canonical_key": "rbi.dor", "name": "Department of Regulation", "short_name": "DoR"},
            {"canonical_key": "rbi.dos", "name": "Department of Supervision", "short_name": "DoS"},
            {
                "canonical_key": "rbi.dpss",
                "name": "Department of Payment and Settlement Systems",
                "short_name": "DPSS",
            },
            {
                "canonical_key": "rbi.fed",
                "name": "Foreign Exchange Department",
                "short_name": "FED",
            },
            {
                "canonical_key": "rbi.fmrd",
                "name": "Financial Markets Regulation Department",
                "short_name": "FMRD",
            },
            {
                "canonical_key": "rbi.cepd",
                "name": "Consumer Education and Protection Department",
                "short_name": "CEPD",
            },
        ],
    },
    {
        "canonical_key": "sebi",
        "name": "Securities and Exchange Board of India",
        "short_name": "SEBI",
        "kind": "securities_regulator",
        "departments": [
            {
                "canonical_key": "sebi.imd",
                "name": "Investment Management Department",
                "short_name": "IMD",
            },
            {
                "canonical_key": "sebi.mrd",
                "name": "Market Regulation Department",
                "short_name": "MRD",
            },
            {
                "canonical_key": "sebi.cfd",
                "name": "Corporation Finance Department",
                "short_name": "CFD",
            },
            {
                "canonical_key": "sebi.afd",
                "name": "Alternative Investment Fund and Foreign Portfolio Investors Department",
                "short_name": "AFD",
            },
            {
                "canonical_key": "sebi.ddhs",
                "name": "Department of Debt and Hybrid Securities",
                "short_name": "DDHS",
            },
            {
                "canonical_key": "sebi.cdmrd",
                "name": "Commodity Derivatives Market Regulation Department",
                "short_name": "CDMRD",
            },
        ],
    },
]

ENTITY_CLASSES: list[dict] = [
    {"canonical_key": "scb", "name": "Scheduled Commercial Bank", "regulator": "rbi"},
    {"canonical_key": "sfb", "name": "Small Finance Bank", "regulator": "rbi"},
    {"canonical_key": "payments_bank", "name": "Payments Bank", "regulator": "rbi"},
    {"canonical_key": "cooperative_bank", "name": "Cooperative Bank", "regulator": "rbi"},
    {"canonical_key": "nbfc", "name": "Non-Banking Financial Company", "regulator": "rbi"},
    {"canonical_key": "nbfc_mfi", "name": "NBFC - Microfinance Institution", "regulator": "rbi"},
    {
        "canonical_key": "nbfc_icc",
        "name": "NBFC - Investment and Credit Company",
        "regulator": "rbi",
    },
    {"canonical_key": "hfc", "name": "Housing Finance Company", "regulator": "rbi"},
    {"canonical_key": "payment_aggregator", "name": "Payment Aggregator", "regulator": "rbi"},
    {"canonical_key": "pso", "name": "Payment System Operator", "regulator": "rbi"},
    {
        "canonical_key": "ppi_issuer",
        "name": "Prepaid Payment Instrument Issuer",
        "regulator": "rbi",
    },
    {"canonical_key": "arc", "name": "Asset Reconstruction Company", "regulator": "rbi"},
    {"canonical_key": "cic", "name": "Credit Information Company", "regulator": "rbi"},
    {"canonical_key": "primary_dealer", "name": "Primary Dealer", "regulator": "rbi"},
    {"canonical_key": "aif", "name": "Alternative Investment Fund", "regulator": "sebi"},
    {"canonical_key": "mutual_fund", "name": "Mutual Fund", "regulator": "sebi"},
    {"canonical_key": "amc", "name": "Asset Management Company", "regulator": "sebi"},
    {"canonical_key": "fpi", "name": "Foreign Portfolio Investor", "regulator": "sebi"},
    {"canonical_key": "stock_broker", "name": "Stock Broker", "regulator": "sebi"},
    {"canonical_key": "depository_participant", "name": "Depository Participant", "regulator": "sebi"},
]

PARENT_ACTS: list[dict] = [
    {
        "canonical_key": "rbi_act_1934",
        "name": "Reserve Bank of India Act, 1934",
        "year": 1934,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "banking_regulation_act_1949",
        "name": "Banking Regulation Act, 1949",
        "year": 1949,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "sebi_act_1992",
        "name": "Securities and Exchange Board of India Act, 1992",
        "year": 1992,
        "anchors_regulator": "sebi",
    },
    {
        "canonical_key": "scra_1956",
        "name": "Securities Contracts (Regulation) Act, 1956",
        "year": 1956,
        "anchors_regulator": "sebi",
    },
    {
        "canonical_key": "pss_act_2007",
        "name": "Payment and Settlement Systems Act, 2007",
        "year": 2007,
        "anchors_regulator": "rbi",
    },
]


async def _get_or_create_node(
    session: AsyncSession,
    *,
    node_type: NodeType,
    canonical_key: str,
    properties: dict,
) -> Node:
    stmt = select(Node).where(
        Node.node_type == node_type.value,
        Node.properties["canonical_key"].astext == canonical_key,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing
    node = Node(node_type=node_type.value, properties=properties)
    session.add(node)
    await session.flush()
    return node


async def _get_or_create_edge(
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


async def seed(session: AsyncSession) -> dict[str, int]:
    """Insert canonical data. Idempotent. Returns counts by node type."""
    regulator_by_key: dict[str, Node] = {}

    for reg in REGULATORS:
        parent = await _get_or_create_node(
            session,
            node_type=NodeType.REGULATOR,
            canonical_key=reg["canonical_key"],
            properties={
                "canonical_key": reg["canonical_key"],
                "name": reg["name"],
                "short_name": reg["short_name"],
                "kind": reg["kind"],
                "is_root": True,
            },
        )
        regulator_by_key[reg["canonical_key"]] = parent
        for dept in reg["departments"]:
            child = await _get_or_create_node(
                session,
                node_type=NodeType.REGULATOR,
                canonical_key=dept["canonical_key"],
                properties={
                    "canonical_key": dept["canonical_key"],
                    "name": dept["name"],
                    "short_name": dept["short_name"],
                    "kind": "department",
                    "parent_regulator": reg["canonical_key"],
                    "is_root": False,
                },
            )
            await _get_or_create_edge(
                session, source=child, target=parent, edge_type=EdgeType.ISSUED_BY
            )

    for ec in ENTITY_CLASSES:
        node = await _get_or_create_node(
            session,
            node_type=NodeType.ENTITY_CLASS,
            canonical_key=ec["canonical_key"],
            properties={
                "canonical_key": ec["canonical_key"],
                "name": ec["name"],
                "regulator": ec["regulator"],
            },
        )
        regulator = regulator_by_key[ec["regulator"]]
        await _get_or_create_edge(
            session, source=node, target=regulator, edge_type=EdgeType.ISSUED_BY
        )

    for act in PARENT_ACTS:
        node = await _get_or_create_node(
            session,
            node_type=NodeType.PARENT_ACT,
            canonical_key=act["canonical_key"],
            properties={
                "canonical_key": act["canonical_key"],
                "name": act["name"],
                "year": act["year"],
                "anchors_regulator": act["anchors_regulator"],
            },
        )
        regulator = regulator_by_key[act["anchors_regulator"]]
        await _get_or_create_edge(
            session, source=regulator, target=node, edge_type=EdgeType.DERIVED_FROM
        )

    await session.commit()

    counts: dict[str, int] = {}
    for nt in NodeType:
        result = await session.execute(
            select(Node).where(Node.node_type == nt.value)
        )
        counts[nt.value] = len(result.scalars().all())
    return counts


async def _main() -> None:
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        counts = await seed(session)
    print("Seed complete. Node counts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
