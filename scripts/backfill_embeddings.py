"""Backfill missing raw_document embeddings (e.g. after an embedding-provider
outage left rows NULL). Batched, committed per batch, safe to re-run.

    DATABASE_URL=... EMBEDDING_PROVIDER=local uv run python scripts/backfill_embeddings.py
"""

from __future__ import annotations

import asyncio

from policyai_extraction.embeddings import embed_text
from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import RawDocument
from sqlalchemy import select

BATCH = 25


async def main() -> None:
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    done = failed = 0
    while True:
        async with sessionmaker() as session:
            rows = (
                (
                    await session.execute(
                        select(RawDocument)
                        .where(RawDocument.embedding.is_(None), RawDocument.raw_text.isnot(None))
                        .limit(BATCH)
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                break
            for doc in rows:
                try:
                    doc.embedding = await embed_text((doc.raw_text or "")[:8000])
                    done += 1
                except Exception as exc:  # noqa: BLE001 - keep going, rerun later
                    failed += 1
                    print(f"  ! {doc.source}:{doc.source_id}: {str(exc)[:100]}")
            await session.commit()
            print(f"embedded {done} (failed {failed})")
    await engine.dispose()
    print(f"DONE: embedded {done}, failed {failed}")


if __name__ == "__main__":
    asyncio.run(main())
