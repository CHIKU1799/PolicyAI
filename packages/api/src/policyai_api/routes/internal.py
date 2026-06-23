"""Internal endpoints (service-to-service). Guarded by a shared secret.

``/internal/map-obligations`` is invoked two ways:
  - event-driven: the Supabase pg_net trigger POSTs a ``regulation_node_id`` when
    a new regulation node is inserted;
  - reconciliation: the Render cron POSTs with no id to map any regulation that
    still lacks an obligation (covers pg_net's fire-and-forget delivery gaps).

Mapping is idempotent, so duplicate deliveries are harmless.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from policyai_extraction.llm import LLMClient
from policyai_extraction.mapping import map_obligation
from policyai_graph.models import Node, NodeType
from policyai_graph.models_app import DEFAULT_ORG_ID, Obligation
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import get_llm, get_session, require_internal_secret

router = APIRouter(prefix="/internal", tags=["internal"])


class MapRequest(BaseModel):
    regulation_node_id: UUID | None = None
    org_id: UUID = DEFAULT_ORG_ID
    limit: int = 50


class MapResponse(BaseModel):
    mapped: int
    skipped: int


@router.post(
    "/map-obligations", response_model=MapResponse, dependencies=[Depends(require_internal_secret)]
)
async def map_obligations(
    req: MapRequest,
    session: AsyncSession = Depends(get_session),
    llm: LLMClient = Depends(get_llm),
) -> MapResponse:
    if req.regulation_node_id is not None:
        targets = [req.regulation_node_id]
    else:
        # Reconciliation: regulations without an obligation for this org.
        mapped_ids = select(Obligation.regulation_node_id).where(Obligation.org_id == req.org_id)
        rows = (
            (
                await session.execute(
                    select(Node.id)
                    .where(Node.node_type == NodeType.REGULATION.value)
                    .where(Node.id.notin_(mapped_ids))
                    .limit(req.limit)
                )
            )
            .scalars()
            .all()
        )
        targets = list(rows)

    mapped = skipped = 0
    for reg_id in targets:
        result = await map_obligation(session, reg_id, llm, org_id=req.org_id)
        if result is not None:
            mapped += 1
        else:
            skipped += 1
        await session.commit()
    return MapResponse(mapped=mapped, skipped=skipped)
