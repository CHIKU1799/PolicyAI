"""CLI: map every ingested regulation that still lacks an obligation, for one org.

Run this after a crawl to populate obligations, requirement-level gaps, tasks and
alerts (the crawl only ingests regulations + their atomic requirements):

    uv run python -m policyai_extraction.map_all

Idempotent and per-regulation isolated: one regulation failing rolls back only
that one and the run continues. Honors the relevance gate, so irrelevant
regulations are skipped without an LLM call.
"""

from __future__ import annotations

import asyncio
import logging
import os
from uuid import UUID

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import Node, NodeType
from policyai_graph.models_app import DEFAULT_ORG_ID, Obligation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction.dbretry import MAX_ATTEMPTS as _MAP_RETRIES
from policyai_extraction.dbretry import is_transient as _is_transient
from policyai_extraction.llm import LLMClient
from policyai_extraction.mapping import map_obligation

log = logging.getLogger("policyai.map")


async def map_unmapped_in_session(
    session: AsyncSession,
    llm: LLMClient,
    *,
    org_id: UUID = DEFAULT_ORG_ID,
    limit: int = 1000,
) -> tuple[int, int]:
    """Map every regulation that lacks an obligation for ``org_id`` using the caller's
    session + LLM. Returns (mapped, skipped). This is the core used both by the CLI
    and inline after a crawl/ingest, so mapping always behaves identically.

    Per-regulation isolated (one failure rolls back only that regulation); honors the
    relevance gate, so regulations that don't apply cost no LLM call.
    """
    mapped = skipped = 0
    mapped_ids = select(Obligation.regulation_node_id).where(Obligation.org_id == org_id)
    targets = (
        (
            await session.execute(
                select(Node.id)
                .where(Node.node_type == NodeType.REGULATION.value)
                .where(Node.id.notin_(mapped_ids))
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    log.info("%d unmapped regulations for org %s", len(targets), org_id)
    failed = 0
    for rid in targets:
        # Retry the regulation on transient connection drops; give up (and log) only
        # on a real error or after exhausting retries — one regulation is never lost
        # silently to a pooler hiccup.
        for attempt in range(1, _MAP_RETRIES + 1):
            try:
                result = await map_obligation(session, rid, llm, org_id=org_id)
                await session.commit()
                if result is not None:
                    mapped += 1
                else:
                    skipped += 1
                break
            except Exception as exc:  # noqa: BLE001 - isolate per-regulation failures
                try:
                    await session.rollback()
                except Exception:  # noqa: BLE001 - rollback on a dead conn can itself fail
                    pass
                if _is_transient(exc) and attempt < _MAP_RETRIES:
                    await asyncio.sleep(1.5 * attempt)
                    log.info("map retry %d/%d for %s (transient)", attempt, _MAP_RETRIES, rid)
                    continue
                failed += 1
                log.warning("map FAILED for %s: %s", rid, str(exc)[:200])
                break
    log.info("mapping done: mapped=%d skipped=%d failed=%d", mapped, skipped, failed)
    return mapped, skipped


async def map_unmapped(org_id: UUID = DEFAULT_ORG_ID, limit: int = 1000) -> tuple[int, int]:
    """CLI/standalone wrapper: own engine + LLM, then delegate to the session core."""
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    llm = LLMClient()
    try:
        async with sessionmaker() as session:
            mapped, skipped = await map_unmapped_in_session(
                session, llm, org_id=org_id, limit=limit
            )
    finally:
        await llm.aclose()
        await engine.dispose()
    log.info("cost: %s", llm.cost.summary())
    return mapped, skipped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    org = os.getenv("MAP_ORG_ID")
    asyncio.run(map_unmapped(UUID(org) if org else DEFAULT_ORG_ID))
