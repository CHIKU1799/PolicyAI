"""Extraction pipeline: one raw document -> structured regulation in the graph.

For each new ``RawDocument`` this:
  1. extracts a structured ``ExtractedRegulation`` (forced tool use),
  2. upserts a ``regulation`` Node and its edges (ISSUED_BY, APPLIES_TO,
     COVERS_TOPIC, HAS_DEADLINE, plus AMENDS/SUPERSEDES/REFERENCES when the
     target regulation already exists),
  3. embeds the document text into ``RawDocument.embedding``,
  4. writes a NEW_REGULATION ``Alert``.

Entity classes resolve against the seeded vocabulary (unknown ones are ignored).
Topics are canonicalized to snake_case and created on demand.
"""

from __future__ import annotations

import re
from pathlib import Path

from policyai_graph.graph_ops import find_node, get_or_create_edge, get_or_create_node
from policyai_graph.models import EdgeType, Node, NodeType, RawDocument
from policyai_graph.models_app import DEFAULT_ORG_ID, Alert, AlertKind
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction.embeddings import embed_text
from policyai_extraction.llm import MODEL_EXTRACTION, LLMClient
from policyai_extraction.schemas import ExtractedRegulation

_PROMPT_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
_REL_RE = re.compile(r"[^a-z0-9]+")


def load_prompt(name: str) -> str:
    """Read a versioned prompt file; the body after the '---' separator is the
    actual system prompt."""
    text = (_PROMPT_DIR / name).read_text(encoding="utf-8")
    return text.split("---", 1)[-1].strip() if "---" in text else text.strip()


def canonical_topic(label: str) -> str:
    return _REL_RE.sub("_", label.strip().lower()).strip("_")


async def process_document(
    session: AsyncSession,
    raw: RawDocument,
    llm: LLMClient,
    *,
    org_id=DEFAULT_ORG_ID,
) -> Node:
    """Extract + upsert one document. Returns the regulation Node. Caller commits."""
    system = load_prompt("regulation_extraction_v1.md")
    prompt = (
        f"Document title: {raw.title}\n"
        f"Source: {raw.source}\n"
        f"Published date: {raw.published_date or 'unknown'}\n\n"
        f"--- DOCUMENT TEXT ---\n{raw.raw_text[:40000]}"
    )
    extracted: ExtractedRegulation = await llm.extract(
        prompt, ExtractedRegulation, system=system, model=MODEL_EXTRACTION
    )

    reg_key = f"{raw.source}:{raw.source_id}"
    reg_node = await get_or_create_node(
        session,
        node_type=NodeType.REGULATION,
        canonical_key=reg_key,
        properties={
            "canonical_key": reg_key,
            "title": extracted.title or raw.title,
            "summary": extracted.summary,
            "regulator": extracted.regulator_key,
            "severity": extracted.severity,
            "source_url": raw.source_url,
            "published_date": str(raw.published_date) if raw.published_date else None,
        },
    )

    # ISSUED_BY -> regulator (department if resolvable, else top-level regulator)
    issuer_key = extracted.department or extracted.regulator_key
    issuer = await find_node(session, node_type=NodeType.REGULATOR, canonical_key=issuer_key)
    if issuer is None:
        issuer = await find_node(
            session, node_type=NodeType.REGULATOR, canonical_key=extracted.regulator_key
        )
    if issuer is not None:
        await get_or_create_edge(
            session, source=reg_node, target=issuer, edge_type=EdgeType.ISSUED_BY
        )

    # APPLIES_TO -> seeded entity classes only
    for ec_key in extracted.entity_classes:
        ec = await find_node(session, node_type=NodeType.ENTITY_CLASS, canonical_key=ec_key)
        if ec is not None:
            await get_or_create_edge(
                session, source=reg_node, target=ec, edge_type=EdgeType.APPLIES_TO
            )

    # COVERS_TOPIC -> topic nodes (created on demand, canonicalized)
    for topic_label in extracted.topics:
        key = canonical_topic(topic_label)
        if not key:
            continue
        topic = await get_or_create_node(
            session,
            node_type=NodeType.TOPIC,
            canonical_key=key,
            properties={"canonical_key": key, "name": topic_label},
        )
        await get_or_create_edge(
            session, source=reg_node, target=topic, edge_type=EdgeType.COVERS_TOPIC
        )

    # HAS_DEADLINE -> deadline nodes
    for dl in extracted.deadlines:
        dl_key = f"{reg_key}:deadline:{canonical_topic(dl.description)[:48]}"
        deadline = await get_or_create_node(
            session,
            node_type=NodeType.DEADLINE,
            canonical_key=dl_key,
            properties={
                "canonical_key": dl_key,
                "description": dl.description,
                "due_date": str(dl.due_date) if dl.due_date else None,
                "relative_text": dl.relative_text,
            },
        )
        await get_or_create_edge(
            session, source=reg_node, target=deadline, edge_type=EdgeType.HAS_DEADLINE
        )

    # AMENDS / SUPERSEDES / REFERENCES -> only when the target regulation exists
    rel_to_edge = {
        "amends": EdgeType.AMENDS,
        "supersedes": EdgeType.SUPERSEDES,
        "references": EdgeType.REFERENCES,
        "derived_from": EdgeType.DERIVED_FROM,
    }
    for ref in extracted.references:
        edge_type = rel_to_edge.get(ref.relationship.lower())
        if edge_type is None:
            continue
        # Stored as a property hint; edge only if we can match an existing reg by title.
        target = await _find_regulation_by_title(session, ref.title)
        if target is not None:
            await get_or_create_edge(session, source=reg_node, target=target, edge_type=edge_type)

    # Link the raw document, embed it, and alert.
    raw.regulation_node_id = reg_node.id
    try:
        raw.embedding = await embed_text(raw.raw_text[:8000])
    except Exception as exc:  # noqa: BLE001 - embedding outage shouldn't drop the extraction
        print(f"[pipeline] embedding failed for {reg_key}: {exc}")

    reg_label = extracted.title or raw.title
    session.add(
        Alert(
            org_id=org_id,
            kind=AlertKind.NEW_REGULATION.value,
            regulation_node_id=reg_node.id,
            message=f"New {extracted.regulator_key.upper()} regulation: {reg_label}",
        )
    )
    return reg_node


async def _find_regulation_by_title(session: AsyncSession, title: str) -> Node | None:
    from sqlalchemy import select

    stmt = (
        select(Node)
        .where(Node.node_type == NodeType.REGULATION.value)
        .where(Node.properties["title"].astext.ilike(f"%{title[:60]}%"))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
