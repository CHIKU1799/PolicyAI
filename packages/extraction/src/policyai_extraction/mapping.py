"""Obligation mapping: one regulation -> obligations + tasks for one company.

Flow:
  1. Graph traversal — collect the regulation's APPLIES_TO entity classes and
     COVERS_TOPIC topics.
  2. Relevance gate — intersect with the company profile. If empty, return
     without calling the LLM (irrelevant regulations cost nothing).
  3. pgvector — pull the company's KB documents nearest the regulation, as gap
     evidence.
  4. Claude — produce an ObligationMapping (obligation + what-changed + gap +
     tasks) with the high-stakes mapping model.
  5. Persist — upsert Obligation (idempotent on org+regulation), create Tasks
     (owners optionally enriched via gbrain), write a NEW_OBLIGATION Alert.

Idempotent: re-running for the same (org, regulation) updates the existing
obligation rather than duplicating it — safe for the fire-and-forget pg_net hook.
"""

from __future__ import annotations

from uuid import UUID

from policyai_graph.models import Edge, EdgeType, Node, NodeType, RawDocument
from policyai_graph.models_app import (
    DEFAULT_ORG_ID,
    Alert,
    AlertKind,
    AuditEvent,
    CompanyDocument,
    CompanyProfile,
    Gap,
    Obligation,
    Task,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction import gbrain_client, notifications, rerank
from policyai_extraction.llm import MODEL_MAPPING, LLMClient
from policyai_extraction.pipeline import load_prompt
from policyai_extraction.schemas import ObligationMapping


async def _targets(session: AsyncSession, reg_id: UUID, edge_type: EdgeType) -> list[str]:
    """Canonical keys of nodes reachable from the regulation by an edge type."""
    stmt = (
        select(Node.properties)
        .join(Edge, Edge.target_id == Node.id)
        .where(Edge.source_id == reg_id, Edge.edge_type == edge_type.value)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [p.get("canonical_key") for p in rows if p and p.get("canonical_key")]


async def _nearest_kb_docs(
    session: AsyncSession, reg_id: UUID, org_id: UUID, k: int = 3
) -> list[CompanyDocument]:
    """Company KB docs closest to the regulation's embedding (gap evidence)."""
    raw = (
        await session.execute(
            select(RawDocument).where(RawDocument.regulation_node_id == reg_id).limit(1)
        )
    ).scalar_one_or_none()
    if raw is None or raw.embedding is None:
        return []
    # Pull a wider vector shortlist, then (optionally) rerank to the best k with
    # an open-source cross-encoder for sharper gap evidence.
    pool = max(k * 4, k) if rerank.is_enabled() else k
    stmt = (
        select(CompanyDocument)
        .where(CompanyDocument.org_id == org_id, CompanyDocument.embedding.isnot(None))
        .order_by(CompanyDocument.embedding.cosine_distance(raw.embedding))
        .limit(pool)
    )
    candidates = list((await session.execute(stmt)).scalars().all())
    if rerank.is_enabled() and len(candidates) > 1:
        query = (raw.raw_text or "")[:1500]
        texts = [(d.raw_text or "")[:1500] for d in candidates]
        order = await rerank.rerank(query, texts, top_k=k)
        return [candidates[i] for i in order]
    return candidates[:k]


async def map_obligation(
    session: AsyncSession,
    regulation_node_id: UUID,
    llm: LLMClient,
    *,
    org_id: UUID = DEFAULT_ORG_ID,
) -> Obligation | None:
    """Map one regulation onto the org's profile. Returns the Obligation, or None
    if the regulation is irrelevant. Caller commits."""
    reg = await session.get(Node, regulation_node_id)
    if reg is None or reg.node_type != NodeType.REGULATION.value:
        return None

    reg_classes = set(await _targets(session, regulation_node_id, EdgeType.APPLIES_TO))
    reg_topics = set(await _targets(session, regulation_node_id, EdgeType.COVERS_TOPIC))

    profile = (
        await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == org_id))
    ).scalar_one_or_none()
    profile_classes = set(profile.entity_classes) if profile else set()
    profile_topics = set(profile.topics) if profile else set()

    # Relevance gate — no profile means we can't judge; skip rather than spend.
    if not profile:
        return None
    class_hit = reg_classes & profile_classes
    topic_hit = reg_topics & profile_topics
    if not class_hit and not topic_hit:
        return None

    kb_docs = await _nearest_kb_docs(session, regulation_node_id, org_id)
    kb_excerpts = (
        "\n\n".join(f"[{d.filename}]\n{(d.raw_text or '')[:1500]}" for d in kb_docs)
        or "(no matching company documents)"
    )

    system = load_prompt("obligation_mapping_v1.md")
    prompt = (
        f"REGULATION\nTitle: {reg.properties.get('title')}\n"
        f"Summary: {reg.properties.get('summary')}\n"
        f"Applies to entity classes: {sorted(reg_classes)}\n"
        f"Topics: {sorted(reg_topics)}\n\n"
        f"COMPANY PROFILE\nEntity classes: {sorted(profile_classes)}\n"
        f"Topics: {sorted(profile_topics)}\n"
        f"Matched on: classes={sorted(class_hit)} topics={sorted(topic_hit)}\n\n"
        f"COMPANY POLICY EXCERPTS (nearest)\n{kb_excerpts}"
    )
    mapping: ObligationMapping = await llm.extract(
        prompt,
        ObligationMapping,
        system=system,
        model=MODEL_MAPPING,
        max_tokens=4096,
    )
    if not mapping.is_relevant:
        return None

    # Upsert the obligation (idempotent on org + regulation).
    obligation = (
        await session.execute(
            select(Obligation).where(
                Obligation.org_id == org_id,
                Obligation.regulation_node_id == regulation_node_id,
            )
        )
    ).scalar_one_or_none()
    if obligation is None:
        obligation = Obligation(org_id=org_id, regulation_node_id=regulation_node_id)
        session.add(obligation)
    obligation.title = mapping.title
    obligation.summary = mapping.summary
    obligation.what_changed = mapping.what_changed
    obligation.gap_analysis = mapping.gap_analysis
    obligation.severity = mapping.severity
    await session.flush()

    # Replace tasks for a clean re-run.
    existing_tasks = (
        (await session.execute(select(Task).where(Task.obligation_id == obligation.id)))
        .scalars()
        .all()
    )
    for t in existing_tasks:
        await session.delete(t)

    company_name = (profile.notes or "").strip() if profile else ""
    for mt in mapping.tasks:
        owner = mt.suggested_owner
        if owner is None and company_name and gbrain_client.is_configured():
            owners = await gbrain_client.suggest_owners(company_name, topic=mapping.title)
            owner = owners[0] if owners else None
        session.add(
            Task(
                org_id=org_id,
                obligation_id=obligation.id,
                title=mt.title,
                description=mt.description,
                owner=owner,
                due_date=mt.due_date,
                priority=mt.priority,
            )
        )

    # Gap register — record the coverage gap the analysis surfaced (one per obligation).
    if mapping.gap_analysis:
        existing_gap = (
            await session.execute(select(Gap).where(Gap.obligation_id == obligation.id))
        ).scalar_one_or_none()
        if existing_gap is None:
            session.add(
                Gap(
                    org_id=org_id,
                    obligation_id=obligation.id,
                    description=mapping.gap_analysis,
                    severity=mapping.severity,
                )
            )

    # Audit trail — append-only governance record.
    session.add(
        AuditEvent(
            org_id=org_id,
            entity_type="obligation",
            entity_id=obligation.id,
            action="obligation_mapped",
            actor="mapping-engine",
            detail={"title": mapping.title, "severity": mapping.severity},
        )
    )

    alert_message = f"New obligation ({mapping.severity}): {mapping.title}"
    session.add(
        Alert(
            org_id=org_id,
            kind=AlertKind.NEW_OBLIGATION.value,
            regulation_node_id=regulation_node_id,
            obligation_id=obligation.id,
            message=alert_message,
        )
    )
    await notifications.notify_alert(
        AlertKind.NEW_OBLIGATION.value, alert_message, detail=mapping.gap_analysis
    )
    return obligation
