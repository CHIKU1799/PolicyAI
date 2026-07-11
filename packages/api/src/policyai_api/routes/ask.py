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
    result = await ask(session, req.question, llm, org_id=req.org_id)
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
