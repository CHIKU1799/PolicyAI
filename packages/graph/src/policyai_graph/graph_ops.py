"""Idempotent upsert helpers for the knowledge graph.

The single source of truth for "get-or-create this node / edge" used by both the
canonical seed (``seed.py``) and the live extraction pipeline. Dedup identity for
nodes is the ``canonical_key`` property; for edges it is the (source, target,
type) triple guarded by ``uq_edge_triple``.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.models import Edge, EdgeType, Node, NodeType


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
