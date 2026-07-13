"""Derive a company's applicability profile from its uploaded documents.

Runs the company_profile prompt over the KB corpus, then (optionally) enriches
with gbrain — resolving the company in the BFSI graph for extra entity-class
signal. Resolved entity classes / regulators are validated against the seeded
graph vocabulary before persisting.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from policyai_extraction.llm import LLMClient
from policyai_extraction.profile_derive import derive_profile_in_session
from pydantic import BaseModel
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


@router.post("/derive", response_model=DeriveResponse)
async def derive_profile(
    req: DeriveRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
    principal: Principal = Depends(resolve_principal),
) -> DeriveResponse:
    org_id = effective_org(principal, req.org_id)
    profile = await derive_profile_in_session(session, llm, org_id, company_name=req.company_name)
    return DeriveResponse(
        entity_classes=profile.entity_classes,
        topics=profile.topics,
        regulators=profile.regulators,
        rationale=profile.__dict__.get("_rationale"),
    )
