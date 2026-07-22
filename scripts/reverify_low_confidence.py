"""Re-run mapping for obligations whose confidence is low or missing.

Obligations under the confidence threshold surface in the UI as "Being
verified" — this job is the backend half of that promise: it re-maps each one
against the org profile and the latest knowledge base, which either lifts the
confidence (better retrieval context, richer KB since first pass) or confirms
the obligation genuinely needs a human look.

map_obligation() is idempotent per (org, regulation), so re-running updates
the existing obligation in place; nothing is duplicated.

    uv run python scripts/reverify_low_confidence.py [--threshold 0.5] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from policyai_extraction.llm import LLMClient
from policyai_extraction.mapping import map_obligation
from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models_app import Obligation
from sqlalchemy import or_, select

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("policyai.reverify")


async def main(threshold: float, limit: int) -> None:
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    llm = LLMClient()
    improved = unchanged = failed = 0
    async with sessionmaker() as session:
        rows = (
            (
                await session.execute(
                    select(Obligation)
                    .where(
                        or_(
                            Obligation.mapping_confidence.is_(None),
                            Obligation.mapping_confidence < threshold,
                        )
                    )
                    .order_by(Obligation.mapping_confidence.asc().nulls_first())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        log.info("re-verifying %d low-confidence obligations (< %.2f)", len(rows), threshold)
        for ob in rows:
            before = ob.mapping_confidence
            try:
                updated = await map_obligation(
                    session, ob.regulation_node_id, llm, org_id=ob.org_id
                )
                await session.commit()
                after = updated.mapping_confidence if updated else None
                if after is not None and (before is None or after > before):
                    improved += 1
                else:
                    unchanged += 1
                log.info("ok  %s  %.2f -> %s", ob.id, before or 0.0, f"{after:.2f}" if after is not None else "n/a")
            except Exception as exc:  # noqa: BLE001 - one obligation failing isn't fatal
                await session.rollback()
                failed += 1
                log.warning("fail %s: %s", ob.id, str(exc)[:200])
    await engine.dispose()
    log.info("done: %d improved, %d unchanged, %d failed", improved, unchanged, failed)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()
    asyncio.run(main(args.threshold, args.limit))
