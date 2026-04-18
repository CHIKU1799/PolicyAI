from __future__ import annotations

import hashlib
from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.models import EMBEDDING_DIM, Edge, EdgeType, Node, NodeType, RawDocument


@pytest.mark.asyncio
async def test_create_and_query_node(session: AsyncSession) -> None:
    node = Node(
        node_type=NodeType.REGULATOR.value,
        properties={"canonical_key": "rbi", "short_name": "RBI"},
    )
    session.add(node)
    await session.commit()
    await session.refresh(node)

    fetched = (
        await session.execute(select(Node).where(Node.id == node.id))
    ).scalar_one()
    assert fetched.node_type == "regulator"
    assert fetched.properties["short_name"] == "RBI"
    assert fetched.created_at is not None


@pytest.mark.asyncio
async def test_jsonb_property_path_query(session: AsyncSession) -> None:
    session.add_all(
        [
            Node(node_type=NodeType.ENTITY_CLASS.value, properties={"canonical_key": "nbfc"}),
            Node(
                node_type=NodeType.ENTITY_CLASS.value, properties={"canonical_key": "nbfc_mfi"}
            ),
            Node(node_type=NodeType.REGULATOR.value, properties={"canonical_key": "rbi"}),
        ]
    )
    await session.commit()

    stmt = select(Node).where(
        Node.node_type == NodeType.ENTITY_CLASS.value,
        Node.properties["canonical_key"].astext == "nbfc_mfi",
    )
    rows = (await session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].properties["canonical_key"] == "nbfc_mfi"


@pytest.mark.asyncio
async def test_create_edge_between_nodes(session: AsyncSession) -> None:
    circular = Node(
        node_type=NodeType.REGULATION.value, properties={"circular_id": "RBI/2024-25/42"}
    )
    regulator = Node(node_type=NodeType.REGULATOR.value, properties={"canonical_key": "rbi"})
    session.add_all([circular, regulator])
    await session.flush()

    edge = Edge(
        source_id=circular.id, target_id=regulator.id, edge_type=EdgeType.ISSUED_BY.value
    )
    session.add(edge)
    await session.commit()

    stmt = select(Edge).where(Edge.source_id == circular.id)
    fetched = (await session.execute(stmt)).scalar_one()
    assert fetched.edge_type == "issued_by"
    assert fetched.target_id == regulator.id


@pytest.mark.asyncio
async def test_edge_cascade_delete_on_node(session: AsyncSession) -> None:
    a = Node(node_type=NodeType.REGULATION.value, properties={"k": "a"})
    b = Node(node_type=NodeType.REGULATOR.value, properties={"k": "b"})
    session.add_all([a, b])
    await session.flush()
    session.add(Edge(source_id=a.id, target_id=b.id, edge_type=EdgeType.ISSUED_BY.value))
    await session.commit()

    await session.delete(a)
    await session.commit()

    remaining = (await session.execute(select(Edge))).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_duplicate_edge_triple_rejected(session: AsyncSession) -> None:
    a = Node(node_type=NodeType.REGULATION.value, properties={"k": "a"})
    b = Node(node_type=NodeType.REGULATOR.value, properties={"k": "b"})
    session.add_all([a, b])
    await session.flush()
    session.add(Edge(source_id=a.id, target_id=b.id, edge_type=EdgeType.ISSUED_BY.value))
    await session.commit()

    session.add(Edge(source_id=a.id, target_id=b.id, edge_type=EdgeType.ISSUED_BY.value))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_raw_document_insert_and_vector_search(session: AsyncSession) -> None:
    e1 = [0.0] * EMBEDDING_DIM
    e1[0] = 1.0
    e2 = [0.0] * EMBEDDING_DIM
    e2[1] = 1.0

    doc1 = RawDocument(
        source="rbi",
        source_id="RBI/2024-25/1",
        source_url="https://rbi.example/c1",
        title="Circular One",
        raw_text="body one",
        published_date=date(2024, 10, 1),
        content_hash=hashlib.sha256(b"body one").hexdigest(),
        embedding=e1,
    )
    doc2 = RawDocument(
        source="sebi",
        source_id="SEBI/2024/9",
        source_url="https://sebi.example/c9",
        title="Circular Two",
        raw_text="body two",
        published_date=date(2024, 11, 1),
        content_hash=hashlib.sha256(b"body two").hexdigest(),
        embedding=e2,
    )
    session.add_all([doc1, doc2])
    await session.commit()

    query = [0.0] * EMBEDDING_DIM
    query[0] = 1.0
    result = await session.execute(
        text(
            "SELECT source_id FROM raw_documents "
            "ORDER BY embedding <=> CAST(:q AS vector) LIMIT 1"
        ),
        {"q": str(query)},
    )
    top = result.scalar_one()
    assert top == "RBI/2024-25/1"


@pytest.mark.asyncio
async def test_raw_document_unique_source_id(session: AsyncSession) -> None:
    d = RawDocument(
        source="rbi",
        source_id="RBI/2024-25/99",
        source_url="u",
        title="t",
        raw_text="r",
        content_hash="h",
    )
    session.add(d)
    await session.commit()

    dup = RawDocument(
        source="rbi",
        source_id="RBI/2024-25/99",
        source_url="u2",
        title="t2",
        raw_text="r2",
        content_hash="h2",
    )
    session.add(dup)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()
