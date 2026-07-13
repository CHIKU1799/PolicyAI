"""'Ask PolicyAI' endpoint — the conversational query layer over the platform."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from policyai_extraction.agent import ask, ask_stream
from policyai_extraction.llm import LLMClient
from policyai_graph.models_app import DEFAULT_ORG_ID
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_llm, get_session

router = APIRouter(prefix="/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str
    org_id: UUID = DEFAULT_ORG_ID


class Citation(BaseModel):
    title: str
    source_url: str
    source: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


@router.post("", response_model=AskResponse)
async def ask_policyai(
    req: AskRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
) -> AskResponse:
    from fastapi import HTTPException

    try:
        result = await ask(session, req.question, llm, org_id=req.org_id)
    except Exception as exc:  # noqa: BLE001 - surface provider errors as a clean 502
        # An unhandled exception would bypass CORS middleware and reach the
        # browser as an opaque network failure; a proper HTTPException keeps
        # the actual message (rate limit, provider outage) visible in the UI.
        raise HTTPException(502, f"LLM provider error: {str(exc)[:300]}") from exc
    return AskResponse(answer=result["answer"], citations=result["citations"])


@router.post("/stream")
async def ask_policyai_stream(
    req: AskRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
) -> StreamingResponse:
    """Server-Sent Events: stream answer tokens as they're generated, then citations.
    The session dependency stays open until the generator finishes."""

    async def event_gen():
        try:
            async for event in ask_stream(session, req.question, llm, org_id=req.org_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 - surface as a stream event, don't 500
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)[:300]})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class ImpactRequest(BaseModel):
    regulation_key: str
    org_id: UUID = DEFAULT_ORG_ID


class ImpactActionOut(BaseModel):
    action: str
    priority: str


class ImpactResponse(BaseModel):
    regulation_key: str
    regulation_title: str
    source_url: str | None
    applicability: str
    overall_severity: str
    summary: str
    affected_areas: list[str]
    key_requirements: list[str]
    suggested_actions: list[ImpactActionOut]


@router.post("/impact-assessment", response_model=ImpactResponse)
async def impact_assessment(
    req: ImpactRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
) -> ImpactResponse:
    """Draft an impact assessment of one regulation for the firm: an analyst
    first pass grounded in the regulation's extracted requirements and the
    org's profile, for a compliance officer to review."""
    from fastapi import HTTPException
    from policyai_extraction.schemas import ImpactAssessment
    from policyai_graph.models import Node
    from policyai_graph.models_app import CompanyProfile, Requirement
    from sqlalchemy import select

    node = (
        await session.execute(
            select(Node).where(Node.properties["canonical_key"].astext == req.regulation_key)
        )
    ).scalar_one_or_none()
    if node is None or node.node_type != "regulation":
        raise HTTPException(404, f"No regulation with key {req.regulation_key!r}")

    reqs = (
        (
            await session.execute(
                select(Requirement).where(Requirement.regulation_node_id == node.id).limit(30)
            )
        )
        .scalars()
        .all()
    )
    profile = (
        await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == req.org_id))
    ).scalar_one_or_none()

    p = node.properties or {}
    req_lines = (
        "\n".join(f"- [{r.requirement_type}] {r.text[:280]}" for r in reqs) or "(none extracted)"
    )
    prof_line = (
        f"entity classes {profile.entity_classes}, topics {profile.topics}, "
        f"regulators {profile.regulators}"
        if profile
        else "(no profile derived yet; assess generically for an Indian regulated firm)"
    )
    prompt = (
        "Draft an impact assessment of this regulation for the firm described below. "
        "Be specific to the firm's profile; do not invent requirements.\n\n"
        f"REGULATION: {p.get('title')}\n"
        f"Regulator: {p.get('regulator')} | Type: {p.get('document_type')} | "
        f"Reference: {p.get('reference_number')} | Published: {p.get('published_date')}\n"
        f"Summary: {p.get('summary')}\n\n"
        f"EXTRACTED REQUIREMENTS:\n{req_lines}\n\n"
        f"FIRM PROFILE: {prof_line}"
    )
    drafted: ImpactAssessment = await llm.extract(
        prompt,
        ImpactAssessment,
        system=(
            "You are a regulatory compliance analyst for Indian BFSI firms. Draft a "
            "grounded, reviewable impact assessment: applicability, impact severity, "
            "affected business areas, the requirements that bite hardest, and concrete "
            "next actions. Ground every statement in the provided requirements."
        ),
    )
    return ImpactResponse(
        regulation_key=req.regulation_key,
        regulation_title=p.get("title") or req.regulation_key,
        source_url=p.get("source_url"),
        applicability=drafted.applicability,
        overall_severity=drafted.overall_severity,
        summary=drafted.summary,
        affected_areas=drafted.affected_areas,
        key_requirements=drafted.key_requirements,
        suggested_actions=[
            ImpactActionOut(action=a.action, priority=a.priority) for a in drafted.suggested_actions
        ],
    )
