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

from policyai_graph.graph_ops import (
    find_node,
    get_or_create_edge,
    get_or_create_node,
    supersede_node,
)
from policyai_graph.models import EdgeType, Node, NodeType, RawDocument
from policyai_graph.models_app import DEFAULT_ORG_ID, Alert, AlertKind, Requirement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction.embeddings import embed_text
from policyai_extraction.llm import OPENAI_TPM_LIMIT, LLMClient, is_payload_too_large
from policyai_extraction.routing import route_model
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
    # Tag complexity and route to a right-sized model (cheap for short notices,
    # strong for dense directions). Pre-extraction we only have length to go on.
    extract_model, complexity = route_model("extraction", raw.raw_text)
    # Free-tier providers (Groq) cap tokens per request; a dense master direction
    # at the full 40k-char clip can exceed it. Start under the provider's cap
    # (chars ~ 3x tokens, minus ~4.2k tokens of system prompt/schema/output) and
    # degrade further instead of failing: the head of a circular carries the
    # title, applicability, and most substantive requirements, so a truncated
    # extraction beats no extraction.
    if OPENAI_TPM_LIMIT:
        clips = (min(40000, max(12000, (OPENAI_TPM_LIMIT - 4200) * 3)), 12000, 6000)
    else:
        clips = (40000, 24000, 12000)
    extracted: ExtractedRegulation | None = None
    for clip in clips:
        prompt = (
            f"Document title: {raw.title}\n"
            f"Source: {raw.source}\n"
            f"Published date: {raw.published_date or 'unknown'}\n\n"
            f"--- DOCUMENT TEXT ---\n{raw.raw_text[:clip]}"
        )
        try:
            extracted = await llm.extract(
                prompt, ExtractedRegulation, system=system, model=extract_model
            )
            break
        except Exception as exc:
            if is_payload_too_large(exc) and clip != clips[-1] and len(raw.raw_text) > clips[-1]:
                continue
            raise
    assert extracted is not None

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
    # Enrich the node with concrete document metadata (JSONB; reassign so the ORM
    # sees the change). Document type / number / penalties live here, not as columns.
    reg_node.properties = {
        **(reg_node.properties or {}),
        "document_type": extracted.document_type,
        "reference_number": extracted.reference_number,
        "penalties": extracted.penalties,
        "compliance_frequency": extracted.compliance_frequency,
        "requirement_count": len(extracted.requirements),
        # Tag the document with the complexity that routed its model — queryable,
        # and reused by the mapping stage to size its (more expensive) model.
        "complexity": complexity,
        "extraction_model": extract_model,
    }
    # Valid-time anchor: prefer a stated effective date, else the publication date.
    effective = extracted.effective_date or raw.published_date
    if effective and reg_node.effective_from is None:
        reg_node.effective_from = effective

    # Persist the atomic requirements (clean re-run: replace any prior set).
    await _persist_requirements(session, reg_node, extracted.requirements, org_id)

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
            # Supersession/amendment retires the predecessor and its obligations,
            # stamping the graph's time axis ("what got invalidated when").
            if edge_type in (EdgeType.SUPERSEDES, EdgeType.AMENDS):
                acted = await supersede_node(
                    session, old=target, new=reg_node, as_of=raw.published_date
                )
                if acted:
                    old_title = (target.properties or {}).get("title", ref.title)
                    session.add(
                        Alert(
                            org_id=org_id,
                            kind=AlertKind.REGULATION_SUPERSEDED.value,
                            regulation_node_id=reg_node.id,
                            message=(
                                f"{extracted.title or raw.title} supersedes "
                                f"“{old_title}” — its obligations were marked superseded"
                            ),
                        )
                    )

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


async def _persist_requirements(
    session: AsyncSession, reg_node: Node, requirements, org_id
) -> None:
    """Replace the regulation's atomic requirements with the freshly extracted set.
    Idempotent across re-runs (delete-then-insert, ordered by ``seq``)."""
    await session.execute(delete(Requirement).where(Requirement.regulation_node_id == reg_node.id))
    for i, r in enumerate(requirements):
        session.add(
            Requirement(
                org_id=org_id,
                regulation_node_id=reg_node.id,
                text=r.text,
                requirement_type=r.requirement_type,
                applies_to=r.applies_to or [],
                frequency=r.frequency,
                citation=r.citation,
                evidence_expected=r.evidence_expected,
                penalty=r.penalty,
                seq=i,
            )
        )


async def _find_regulation_by_title(session: AsyncSession, title: str) -> Node | None:
    stmt = (
        select(Node)
        .where(Node.node_type == NodeType.REGULATION.value)
        .where(Node.properties["title"].astext.ilike(f"%{title[:60]}%"))
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()
