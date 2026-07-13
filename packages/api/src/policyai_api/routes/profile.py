"""Derive a company's applicability profile from its uploaded documents.

Runs the company_profile prompt over the KB corpus, then (optionally) enriches
with gbrain — resolving the company in the BFSI graph for extra entity-class
signal. Resolved entity classes / regulators are validated against the seeded
graph vocabulary before persisting.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from policyai_extraction import gbrain_client
from policyai_extraction.llm import MODEL_MAPPING, LLMClient
from policyai_extraction.pipeline import load_prompt
from policyai_extraction.schemas import CompanyProfileExtraction
from policyai_graph.graph_ops import find_node
from policyai_graph.models import NodeType
from policyai_graph.models_app import CompanyDocument, CompanyProfile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, effective_org, resolve_principal
from policyai_api.deps import get_llm, get_session

router = APIRouter(prefix="/profile", tags=["profile"])


class DeriveRequest(BaseModel):
    org_id: UUID | None = None  # honored only for platform admins
    company_name: str | None = None


class DeriveResponse(BaseModel):
    entity_classes: list[str]
    topics: list[str]
    regulators: list[str]
    rationale: str | None = None


async def _valid_entity_classes(session: AsyncSession, keys: list[str]) -> list[str]:
    out: list[str] = []
    for k in keys:
        if await find_node(session, node_type=NodeType.ENTITY_CLASS, canonical_key=k):
            out.append(k)
    return out


@router.post("/derive", response_model=DeriveResponse)
async def derive_profile(
    req: DeriveRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
    principal: Principal = Depends(resolve_principal),
) -> DeriveResponse:
    org_id = effective_org(principal, req.org_id)
    docs = (
        (
            await session.execute(
                select(CompanyDocument).where(
                    CompanyDocument.org_id == org_id,
                    CompanyDocument.raw_text.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )
    corpus = "\n\n".join(f"[{d.filename}]\n{(d.raw_text or '')[:3000]}" for d in docs)

    gbrain_hint = ""
    if req.company_name and gbrain_client.is_configured():
        company = await gbrain_client.find_company(req.company_name)
        if company:
            gbrain_hint = f"\n\nGBRAIN MATCH (BFSI graph):\n{company}"

    extracted: CompanyProfileExtraction = await llm.extract(
        f"COMPANY DOCUMENTS:\n{corpus or '(none uploaded)'}{gbrain_hint}",
        CompanyProfileExtraction,
        system=load_prompt("company_profile_v1.md"),
        model=MODEL_MAPPING,
    )

    entity_classes = await _valid_entity_classes(session, extracted.entity_classes)

    profile = (
        await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == org_id))
    ).scalar_one_or_none()
    if profile is None:
        profile = CompanyProfile(org_id=org_id)
        session.add(profile)
    profile.entity_classes = entity_classes
    profile.topics = extracted.topics
    profile.regulators = extracted.regulators
    # Stash the company name in notes for downstream gbrain owner lookups.
    if req.company_name:
        profile.notes = req.company_name
    await session.commit()

    return DeriveResponse(
        entity_classes=entity_classes,
        topics=extracted.topics,
        regulators=extracted.regulators,
        rationale=extracted.rationale,
    )
