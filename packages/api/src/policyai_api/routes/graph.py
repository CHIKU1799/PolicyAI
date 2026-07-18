"""Knowledge-graph endpoints for the website's graph explorer.

``/graph/subgraph`` returns a ``{nodes, links}`` payload react-force-graph-2d can
render directly, centered on a node (1-2 hop neighborhood) or, with no center, a
hub-anchored overview sample. ``/graph/search`` powers the center typeahead and
``/graph/stats`` the header counters.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from policyai_graph.models import Edge, Node
from pydantic import BaseModel
from sqlalchemy import func, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_session

router = APIRouter(prefix="/graph", tags=["graph"])


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    key: str | None = None
    props: dict = {}


class GraphLink(BaseModel):
    source: str
    target: str
    type: str


class Subgraph(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


class SearchHit(BaseModel):
    key: str
    label: str
    type: str


class GraphStats(BaseModel):
    nodes: int
    edges: int
    node_types: dict[str, int]
    edge_types: dict[str, int]


# Node-detail fields worth showing in the explorer's side panel.
_DETAIL_KEYS = (
    "summary",
    "regulator",
    "severity",
    "document_type",
    "reference_number",
    "published_date",
    "source_url",
    "requirement_count",
    "name",
)


def _label(node: Node) -> str:
    p = node.properties or {}
    return p.get("short_name") or p.get("name") or p.get("title") or p.get("canonical_key") or "?"


def _to_graph_node(node: Node) -> GraphNode:
    p = node.properties or {}
    return GraphNode(
        id=str(node.id),
        label=_label(node),
        type=node.node_type,
        key=p.get("canonical_key"),
        props={k: p[k] for k in _DETAIL_KEYS if p.get(k) is not None},
    )


@router.get("/stats", response_model=GraphStats)
async def stats(session: AsyncSession = Depends(get_session)) -> GraphStats:
    node_rows = (
        await session.execute(select(Node.node_type, func.count()).group_by(Node.node_type))
    ).all()
    edge_rows = (
        await session.execute(select(Edge.edge_type, func.count()).group_by(Edge.edge_type))
    ).all()
    node_types = {t: c for t, c in node_rows}
    edge_types = {t: c for t, c in edge_rows}
    return GraphStats(
        nodes=sum(node_types.values()),
        edges=sum(edge_types.values()),
        node_types=node_types,
        edge_types=edge_types,
    )


@router.get("/search", response_model=list[SearchHit])
async def search(
    q: str = Query(min_length=2, max_length=80),
    limit: int = Query(default=12, le=25),
    session: AsyncSession = Depends(get_session),
) -> list[SearchHit]:
    pattern = f"%{q}%"
    rows = (
        (
            await session.execute(
                select(Node)
                .where(
                    or_(
                        Node.properties["title"].astext.ilike(pattern),
                        Node.properties["name"].astext.ilike(pattern),
                        Node.properties["canonical_key"].astext.ilike(pattern),
                        Node.properties["reference_number"].astext.ilike(pattern),
                    )
                )
                # regulators/entity classes/topics first (small types make the
                # useful anchors), then newest regulations
                .order_by(Node.node_type == "regulation", Node.created_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        SearchHit(
            key=(n.properties or {}).get("canonical_key") or str(n.id),
            label=_label(n),
            type=n.node_type,
        )
        for n in rows
        if (n.properties or {}).get("canonical_key")
    ]


async def _edges_touching(session: AsyncSession, node_ids: set) -> list[Edge]:
    return (
        (
            await session.execute(
                select(Edge).where(or_(Edge.source_id.in_(node_ids), Edge.target_id.in_(node_ids)))
            )
        )
        .scalars()
        .all()
    )


@router.get("/subgraph", response_model=Subgraph)
async def subgraph(
    center: str | None = Query(default=None, description="canonical_key to center on"),
    hops: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=200, le=600),
    session: AsyncSession = Depends(get_session),
) -> Subgraph:
    if center:
        # A key can exist as both an entity_class and a topic (e.g. "nbfc");
        # prefer the structural anchor types so centering behaves predictably.
        candidates = (
            (
                await session.execute(
                    select(Node).where(Node.properties["canonical_key"].astext == center)
                )
            )
            .scalars()
            .all()
        )
        _pref = {"entity_class": 0, "regulator": 1, "regulation": 2, "parent_act": 3, "topic": 4}
        root = min(candidates, key=lambda n: _pref.get(n.node_type, 9), default=None)
        if root is None:
            return Subgraph(nodes=[], links=[])
        edges = await _edges_touching(session, {root.id})
        if hops == 2:
            frontier = {e.source_id for e in edges} | {e.target_id for e in edges}
            frontier.discard(root.id)
            if frontier:
                second = await _edges_touching(session, frontier)
                seen = {e.id for e in edges}
                edges = (
                    edges + [e for e in second if e.id not in seen][: max(0, limit - len(edges))]
                )
        node_ids = {e.source_id for e in edges} | {e.target_id for e in edges} | {root.id}
    else:
        # Overview: anchor on the highest-degree hubs (regulators, big entity
        # classes, hot topics) instead of an arbitrary first-N-edges slice.
        degree = union_all(
            select(Edge.source_id.label("nid")), select(Edge.target_id.label("nid"))
        ).subquery()
        hubs = (
            await session.execute(
                select(degree.c.nid).group_by(degree.c.nid).order_by(func.count().desc()).limit(12)
            )
        ).scalars()
        edges = (await _edges_touching(session, set(hubs)))[:limit]
        node_ids = {e.source_id for e in edges} | {e.target_id for e in edges}

    nodes = (
        (await session.execute(select(Node).where(Node.id.in_(node_ids)))).scalars().all()
        if node_ids
        else []
    )
    return Subgraph(
        nodes=[_to_graph_node(n) for n in nodes],
        links=[
            GraphLink(source=str(e.source_id), target=str(e.target_id), type=e.edge_type)
            for e in edges
        ],
    )
