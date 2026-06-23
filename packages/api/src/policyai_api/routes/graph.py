"""Knowledge-graph subgraph assembly for the force-graph visualization.

Returns a ``{nodes, links}`` payload react-force-graph-2d can render directly.
Centered on a node (by canonical_key) with a 1-2 hop neighborhood, or a capped
sample of the whole graph when no center is given.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from policyai_graph.models import Edge, Node
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_session

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNode(BaseModel):
    id: str
    label: str
    type: str


class GraphLink(BaseModel):
    source: str
    target: str
    type: str


class Subgraph(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


def _label(node: Node) -> str:
    p = node.properties or {}
    return p.get("short_name") or p.get("name") or p.get("title") or p.get("canonical_key") or "?"


@router.get("/subgraph", response_model=Subgraph)
async def subgraph(
    center: str | None = Query(default=None, description="canonical_key to center on"),
    limit: int = Query(default=150, le=500),
    session: AsyncSession = Depends(get_session),
) -> Subgraph:
    if center:
        root = (
            await session.execute(
                select(Node).where(Node.properties["canonical_key"].astext == center).limit(1)
            )
        ).scalar_one_or_none()
        if root is None:
            return Subgraph(nodes=[], links=[])
        edges = (
            (
                await session.execute(
                    select(Edge).where(or_(Edge.source_id == root.id, Edge.target_id == root.id))
                )
            )
            .scalars()
            .all()
        )
    else:
        edges = (await session.execute(select(Edge).limit(limit))).scalars().all()

    node_ids = {e.source_id for e in edges} | {e.target_id for e in edges}
    if center and root is not None:
        node_ids.add(root.id)
    nodes = (
        (await session.execute(select(Node).where(Node.id.in_(node_ids)))).scalars().all()
        if node_ids
        else []
    )

    return Subgraph(
        nodes=[GraphNode(id=str(n.id), label=_label(n), type=n.node_type) for n in nodes],
        links=[
            GraphLink(source=str(e.source_id), target=str(e.target_id), type=e.edge_type)
            for e in edges
        ],
    )
