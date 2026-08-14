"""Agentic assist for the controls lifecycle.

POST /controls/suggest drafts controls for the obligations the user picked:
grounded in the obligation text and the org's existing control register (so
suggestions extend it instead of duplicating it). The UI shows the drafts for
review; nothing is created until the user accepts, keeping the human in the
loop on what becomes part of the compliance posture.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from policyai_extraction.llm import LLMClient
from policyai_graph.models_app import Control, Obligation
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, effective_org, resolve_principal
from policyai_api.deps import get_llm, get_session
from policyai_api.ratelimit import rate_limited

router = APIRouter(prefix="/controls", tags=["controls"])

MAX_OBLIGATIONS = 3


class SuggestRequest(BaseModel):
    obligation_ids: list[UUID] = Field(min_length=1, max_length=MAX_OBLIGATIONS)
    org_id: UUID | None = None


class SuggestedControl(BaseModel):
    title: str = Field(description="Short imperative control name, e.g. 'Quarterly KYC file audit'")
    description: str = Field(
        description="What the check does, what it samples, and what evidence it produces"
    )
    control_type: str = Field(description="One of: preventive, detective, corrective")
    frequency: str = Field(
        description="One of: daily, weekly, monthly, quarterly, half-yearly, annual"
    )
    rationale: str = Field(description="One sentence: why this control satisfies the obligation(s)")


class ControlSuggestions(BaseModel):
    suggestions: list[SuggestedControl] = Field(
        min_length=1, max_length=3, description="1-3 proposed controls, most important first"
    )


class SuggestResponse(BaseModel):
    suggestions: list[SuggestedControl]


@router.post(
    "/suggest",
    response_model=SuggestResponse,
    dependencies=[Depends(rate_limited("suggest_controls"))],
)
async def suggest_controls(
    req: SuggestRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
    principal: Principal = Depends(resolve_principal),
) -> SuggestResponse:
    org_id = effective_org(principal, req.org_id)

    obligations = (
        (
            await session.execute(
                select(Obligation).where(
                    Obligation.id.in_(req.obligation_ids), Obligation.org_id == org_id
                )
            )
        )
        .scalars()
        .all()
    )
    if not obligations:
        raise HTTPException(404, "No matching obligations in your org")

    existing = (
        await session.execute(
            select(Control.ref_code, Control.title)
            .where(Control.org_id == org_id)
            .order_by(Control.ref_code)
            .limit(40)
        )
    ).all()

    obl_lines = "\n".join(
        f"- [{o.severity}] {o.title}\n"
        f"  Summary: {(o.summary or '')[:400]}\n"
        f"  Citation: {o.regulatory_citation or 'n/a'} | Evidence required: "
        f"{(o.evidence_required or 'n/a')[:200]}"
        for o in obligations
    )
    existing_lines = (
        "\n".join(f"- {ref or '?'}: {title}" for ref, title in existing) or "(none yet)"
    )
    prompt = (
        "Propose operational controls for the obligation(s) below. A control is a "
        "concrete, testable check the firm's team runs on a schedule (sample review, "
        "reconciliation, maker-checker gate, automated monitor with manual review).\n\n"
        f"OBLIGATION(S):\n{obl_lines}\n\n"
        f"EXISTING CONTROL REGISTER (do not duplicate these):\n{existing_lines}"
    )
    drafted: ControlSuggestions = await llm.extract(
        prompt,
        ControlSuggestions,
        system=(
            "You are a compliance operations designer for Indian BFSI firms. Propose "
            "controls that are specific, testable and auditable: name the sample or "
            "population checked, the cadence, and the evidence produced. Prefer one "
            "strong control over many weak ones. Ground everything in the obligation "
            "text; do not invent regulatory requirements."
        ),
        tool_name="record_controls",
        tool_description="Record the proposed controls.",
    )
    # The model occasionally free-texts type/frequency; normalize to the app's vocab.
    valid_types = {"preventive", "detective", "corrective"}
    valid_freq = {"daily", "weekly", "monthly", "quarterly", "half-yearly", "annual"}
    for s in drafted.suggestions:
        s.control_type = s.control_type.strip().lower()
        if s.control_type not in valid_types:
            s.control_type = "detective"
        s.frequency = s.frequency.strip().lower()
        if s.frequency not in valid_freq:
            s.frequency = "quarterly"
    return SuggestResponse(suggestions=drafted.suggestions)
