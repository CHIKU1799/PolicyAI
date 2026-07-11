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
    CoverageStatus,
    Gap,
    Obligation,
    Requirement,
    Severity,
    Task,
    TaskStatus,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction import gbrain_client, notifications, rerank
from policyai_extraction.grounding import is_grounded
from policyai_extraction.llm import LLMClient
from policyai_extraction.pipeline import load_prompt
from policyai_extraction.routing import model_for, route_model, routing_enabled
from policyai_extraction.schemas import ObligationMapping

# Below this the mapping is surfaced for human review rather than trusted outright.
LOW_CONFIDENCE_THRESHOLD = 0.5

# Parent classes a company is also subject to. An NBFC-MFI is an NBFC; a payment
# aggregator is a payment-system operator; etc. Keeps obligation matching from
# missing regulations addressed to the broader class.
ENTITY_CLASS_PARENTS: dict[str, list[str]] = {
    "nbfc_mfi": ["nbfc"],
    "nbfc_icc": ["nbfc"],
    "hfc": ["nbfc"],
    "arc": ["nbfc"],
    "payment_aggregator": ["pso"],
    "ppi_issuer": ["pso"],
    "sfb": ["scb"],
    "payments_bank": ["scb"],
}


def _clip(value: str | None, n: int) -> str | None:
    """Truncate to a column's width so a long model value never hard-fails the write."""
    return value[:n] if value else value


# Map the model's per-requirement status onto a coverage class. 'gap' is the legacy
# label for 'missing' (older prompt), kept so old outputs still classify.
_COVERAGE_ALIASES = {
    "covered": CoverageStatus.COVERED.value,
    "partial": CoverageStatus.PARTIAL.value,
    "missing": CoverageStatus.MISSING.value,
    "gap": CoverageStatus.MISSING.value,
    "conflicting": CoverageStatus.CONFLICTING.value,
    "conflict": CoverageStatus.CONFLICTING.value,
}
# A conflict is a live violation — never let it be filed below 'high'.
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _coverage_status(raw: str | None) -> str:
    return _COVERAGE_ALIASES.get((raw or "").strip().lower(), CoverageStatus.MISSING.value)


def _attribute_doc(quote: str | None, kb_docs: list[CompanyDocument]) -> tuple[str | None, object]:
    """Return (grounded_quote, evidence_doc_id): keep the quote only if it actually
    appears in a policy doc (else it's a hallucinated citation), and attribute it to
    that doc. Uses a normalized-substring match tolerant of whitespace differences."""
    q = " ".join((quote or "").split())
    if len(q) < 12:
        return None, None
    needle = q.lower()
    for d in kb_docs:
        hay = " ".join((d.raw_text or "").split()).lower()
        if needle in hay:
            return quote, d.id
        # tolerate the model quoting a fragment: match on a long-enough prefix
        if len(needle) > 40 and needle[:40] in hay:
            return quote, d.id
    return None, None


def _expand_classes(classes: set[str]) -> set[str]:
    out = set(classes)
    for c in classes:
        out.update(ENTITY_CLASS_PARENTS.get(c, []))
    return out


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
    # Expand the company's classes with their parents: an NBFC-MFI is also an NBFC,
    # so it is subject to regulations addressed to the general 'nbfc' class.
    profile_classes = _expand_classes(set(profile.entity_classes)) if profile else set()
    profile_topics = set(profile.topics) if profile else set()

    # Relevance gate — no profile means we can't judge; skip rather than spend.
    if not profile:
        return None
    class_hit = reg_classes & profile_classes
    topic_hit = reg_topics & profile_topics
    # An entity-class match is the strong signal and always qualifies. A topic-only
    # match must also come from a regulator the company is subject to — otherwise an
    # incidental shared topic (e.g. 'kyc') makes, say, a SEBI adviser circular look
    # relevant to an RBI-only NBFC. This trims false-positive LLM calls.
    reg_regulator = (reg.properties or {}).get("regulator")
    profile_regulators = set(profile.regulators or [])
    regulator_ok = (not profile_regulators) or (reg_regulator in profile_regulators)
    if not class_hit and not (topic_hit and regulator_ok):
        return None

    kb_docs = await _nearest_kb_docs(session, regulation_node_id, org_id)
    kb_excerpts = (
        "\n\n".join(f"[{d.filename}]\n{(d.raw_text or '')[:1500]}" for d in kb_docs)
        or "(no matching company documents)"
    )

    # The regulation's atomic requirements ground the obligation in specifics.
    reqs = (
        (
            await session.execute(
                select(Requirement)
                .where(Requirement.regulation_node_id == regulation_node_id)
                .order_by(Requirement.seq)
            )
        )
        .scalars()
        .all()
    )
    # Number the requirements so the model's `requirement_index` references a
    # specific row rather than guessing an order — keeps requirement-level gaps
    # pinned to the right requirement.
    req_text = (
        "\n".join(
            f"{i}. [{r.requirement_type}] {r.text}"
            + (f" (cite {r.citation})" if r.citation else "")
            for i, r in enumerate(reqs)
        )
        or "(none extracted)"
    )

    system = load_prompt("obligation_mapping_v1.md")
    prompt = (
        f"REGULATION\nTitle: {reg.properties.get('title')}\n"
        f"Summary: {reg.properties.get('summary')}\n"
        f"Document: {reg.properties.get('document_type')} "
        f"{reg.properties.get('reference_number') or ''}\n"
        f"Applies to entity classes: {sorted(reg_classes)}\n"
        f"Topics: {sorted(reg_topics)}\n"
        f"REQUIREMENTS:\n{req_text}\n\n"
        f"COMPANY PROFILE\nEntity classes: {sorted(profile_classes)}\n"
        f"Topics: {sorted(profile_topics)}\n"
        f"Matched on: classes={sorted(class_hit)} topics={sorted(topic_hit)}\n\n"
        f"COMPANY POLICY EXCERPTS (nearest)\n{kb_excerpts}"
    )
    # Route the (expensive) mapping model by the regulation's complexity. Reuse the
    # tag stored at extraction time when present; otherwise derive it from the
    # regulation's substance (summary + requirements + how dense it is).
    stored_complexity = (reg.properties or {}).get("complexity")
    if routing_enabled() and stored_complexity in ("low", "medium", "high"):
        mapping_model = model_for("mapping", stored_complexity)
    else:
        reg_substance = f"{reg.properties.get('summary') or ''}\n{req_text}"
        mapping_model = route_model(
            "mapping",
            reg_substance,
            (reg.properties or {}).get("document_type"),
            reference_count=len(reqs),
        )[0]
    mapping: ObligationMapping = await llm.extract(
        prompt,
        ObligationMapping,
        system=system,
        model=mapping_model,
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
    is_new = obligation is None
    if obligation is None:
        obligation = Obligation(org_id=org_id, regulation_node_id=regulation_node_id)
        session.add(obligation)
    obligation.title = mapping.title
    obligation.summary = mapping.summary
    obligation.what_changed = mapping.what_changed
    obligation.gap_analysis = mapping.gap_analysis
    # Clamp the narrow enum-ish columns so an over-long model value truncates rather
    # than hard-failing the whole obligation write (severity=16, *_type/frequency=32).
    obligation.severity = _clip(mapping.severity, 16)
    obligation.obligation_type = _clip(mapping.obligation_type, 32)
    obligation.frequency = _clip(mapping.frequency, 32)
    obligation.regulatory_citation = mapping.regulatory_citation
    obligation.penalty_summary = mapping.penalty_summary
    obligation.evidence_required = mapping.evidence_required
    obligation.mapping_confidence = mapping.confidence
    obligation.relevance_rationale = mapping.relevance_rationale
    if obligation.effective_date is None:
        obligation.effective_date = reg.effective_from
    await session.flush()

    # Refresh tasks without destroying human work. A re-map regenerates the
    # suggested task list, but any task a person has started, finished, blocked, or
    # reassigned is preserved — only untouched TODO tasks are swept and rebuilt.
    existing_tasks = (
        (await session.execute(select(Task).where(Task.obligation_id == obligation.id)))
        .scalars()
        .all()
    )
    preserved_titles: set[str] = set()
    for t in existing_tasks:
        if t.status == TaskStatus.TODO.value and t.owner is None:
            await session.delete(t)
        else:
            preserved_titles.add(t.title.strip().lower())

    company_name = (profile.notes or "").strip() if profile else ""
    for mt in mapping.tasks:
        # Don't recreate a task a human already owns/works under a matching title.
        if mt.title.strip().lower() in preserved_titles:
            continue
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

    # Obligation-level summary gap (requirement_id is NULL). Upsert the single summary.
    if mapping.gap_analysis:
        summary_gap = (
            await session.execute(
                select(Gap).where(Gap.obligation_id == obligation.id, Gap.requirement_id.is_(None))
            )
        ).scalar_one_or_none()
        if summary_gap is None:
            session.add(
                Gap(
                    org_id=org_id,
                    obligation_id=obligation.id,
                    description=mapping.gap_analysis,
                    severity=mapping.severity,
                )
            )
        else:
            summary_gap.description = mapping.gap_analysis

    # Requirement-level gaps — one Gap per uncovered/partial requirement, tied to it.
    # Idempotent: drop and rebuild the requirement-scoped gaps for this obligation.
    await session.execute(
        delete(Gap).where(Gap.obligation_id == obligation.id, Gap.requirement_id.isnot(None))
    )
    ungrounded_gaps = 0
    conflicts: list[str] = []
    for rg in mapping.requirement_gaps:
        coverage = _coverage_status(rg.status)
        # 'covered' requirements are not gaps — coverage % is derived from the
        # requirement count minus the persisted (non-covered) gaps.
        if coverage == CoverageStatus.COVERED.value:
            continue
        if not (0 <= rg.requirement_index < len(reqs)):
            continue
        req = reqs[rg.requirement_index]
        # Ground the gap text: it must be about this requirement (or the policy
        # excerpts we showed the model). If the model's description shares no content
        # with either, treat it as a hallucination and fall back to a description
        # derived straight from the requirement — never persist an invented gap.
        grounding_corpus = f"{req.text}\n{kb_excerpts}"
        description = (rg.gap_description or "").strip()
        if not description or not is_grounded(description, grounding_corpus):
            if description:
                ungrounded_gaps += 1
            description = f"{coverage}: {req.text}"
        # A conflict is a live violation — never file it below 'high'.
        severity = rg.severity or mapping.severity
        if coverage == CoverageStatus.CONFLICTING.value and _SEVERITY_RANK.get(
            severity, 1
        ) < _SEVERITY_RANK[Severity.HIGH.value]:
            severity = Severity.HIGH.value
        # Keep the cited policy passage only if it truly appears in a policy doc,
        # and attribute it — a fabricated quote is worse than none for a penalty case.
        evidence_quote, evidence_doc_id = _attribute_doc(rg.evidence_quote, kb_docs)
        session.add(
            Gap(
                org_id=org_id,
                obligation_id=obligation.id,
                requirement_id=req.id,
                description=description,
                severity=severity,
                coverage_status=coverage,
                evidence_quote=evidence_quote,
                evidence_doc_id=evidence_doc_id,
            )
        )
        if coverage == CoverageStatus.CONFLICTING.value:
            conflicts.append(req.text)

    # Audit trail — append-only governance record. Carries the calibration signal
    # (predicted confidence, whether it's below the review threshold, and how many
    # gaps the model hallucinated) so confidence can be tuned against outcomes later.
    low_confidence = (mapping.confidence or 0.0) < LOW_CONFIDENCE_THRESHOLD
    session.add(
        AuditEvent(
            org_id=org_id,
            entity_type="obligation",
            entity_id=obligation.id,
            action="obligation_mapped",
            actor="mapping-engine",
            detail={
                "title": mapping.title,
                "severity": mapping.severity,
                "confidence": mapping.confidence,
                "low_confidence": low_confidence,
                "ungrounded_gaps": ungrounded_gaps,
                "is_new": is_new,
                "mapping_model": mapping_model,
                "complexity": stored_complexity,
            },
        )
    )

    # Only fire a NEW_OBLIGATION alert when the obligation is genuinely new — a
    # re-map of the same (org, regulation) must not spam the alert feed each run.
    if is_new:
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

    # A policy conflict is a live violation → always alert, even on a re-map, since a
    # newly-detected contradiction is the whole point of the product (avoid penalties).
    if conflicts:
        existing_conflict_alert = (
            await session.execute(
                select(Alert).where(
                    Alert.obligation_id == obligation.id,
                    Alert.kind == AlertKind.POLICY_CONFLICT.value,
                )
            )
        ).scalar_one_or_none()
        if existing_conflict_alert is None:
            conflict_message = (
                f"Policy conflict ({len(conflicts)}) on {mapping.title}: "
                f"the firm's policy contradicts this regulation"
            )
            session.add(
                Alert(
                    org_id=org_id,
                    kind=AlertKind.POLICY_CONFLICT.value,
                    regulation_node_id=regulation_node_id,
                    obligation_id=obligation.id,
                    message=conflict_message,
                )
            )
            await notifications.notify_alert(
                AlertKind.POLICY_CONFLICT.value, conflict_message, detail=conflicts[0]
            )
    return obligation
