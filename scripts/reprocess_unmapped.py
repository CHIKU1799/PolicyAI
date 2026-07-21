"""Re-run extraction for raw documents that never got linked to a regulation node.

A document ends up with regulation_node_id NULL when its original
process_document() call failed (LLM error, deadlock, session reset). The crawl
only processes newly fetched docs, so these stragglers stay unmapped until
reprocessed. Idempotent and per-doc isolated, same as the runner.

    uv run python scripts/reprocess_unmapped.py [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from policyai_extraction.llm import LLMClient
from policyai_extraction.pipeline import process_document
from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import RawDocument
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("policyai.reprocess")


async def main(limit: int) -> None:
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    llm = LLMClient()
    ok = failed = 0
    async with sessionmaker() as session:
        docs = (
            (
                await session.execute(
                    select(RawDocument)
                    .where(RawDocument.regulation_node_id.is_(None))
                    .order_by(RawDocument.published_date.desc().nulls_last())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        log.info("reprocessing %d unmapped documents", len(docs))
        for doc in docs:
            try:
                await process_document(session, doc, llm)
                await session.commit()
                ok += 1
                log.info("ok  %s:%s %s", doc.source, doc.source_id, doc.title[:70])
            except Exception as exc:  # noqa: BLE001 - one doc failing isn't fatal
                await session.rollback()
                failed += 1
                log.warning("fail %s:%s: %s", doc.source, doc.source_id, str(exc)[:200])
    await engine.dispose()
    log.info("done: %d reprocessed, %d failed", ok, failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(main(args.limit))
