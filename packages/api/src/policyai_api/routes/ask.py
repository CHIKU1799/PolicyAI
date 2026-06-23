"""'Ask PolicyAI' endpoint — the conversational query layer over the platform."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from policyai_extraction.agent import ask
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
    result = await ask(session, req.question, llm, org_id=req.org_id)
    return AskResponse(answer=result["answer"], citations=result["citations"])
