"""Backfill missing published dates for RBI id-enumerated documents.

The RBI notification page carries its date in the body text (e.g. a
"July 12, 2026" line near the header); the id-range backfill didn't parse it.
Recover it by regex from the stored raw_text and stamp both the raw document
and the regulation node (plus effective_from when empty).

    DATABASE_URL=... uv run python scripts/backfill_dates.py
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import Node, RawDocument
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
# "July 12, 2026" / "12 July 2026" / "12 July, 2026"
_PATTERNS = [
    re.compile(rf"\b({MONTHS})\s+(\d{{1,2}}),?\s+(\d{{4}})\b"),
    re.compile(rf"\b(\d{{1,2}})\s+({MONTHS}),?\s+(\d{{4}})\b"),
]


def find_date(text: str) -> date | None:
    head = (text or "")[:2500]
    for pat in _PATTERNS:
        m = pat.search(head)
        if not m:
            continue
        g = m.groups()
        try:
            if g[0].isdigit():
                d = datetime.strptime(f"{g[0]} {g[1]} {g[2]}", "%d %B %Y").date()
            else:
                d = datetime.strptime(f"{g[1]} {g[0]} {g[2]}", "%d %B %Y").date()
        except ValueError:
            continue
        if date(1990, 1, 1) <= d <= date.today():
            return d
    return None


async def main() -> None:
    engine = make_engine()
    fixed = skipped = 0
    async with make_sessionmaker(engine)() as session:
        docs = (
            (
                await session.execute(
                    select(RawDocument).where(
                        RawDocument.published_date.is_(None), RawDocument.raw_text.isnot(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        print(f"{len(docs)} documents without a published date")
        for doc in docs:
            d = find_date(doc.raw_text or "")
            if not d:
                skipped += 1
                continue
            doc.published_date = d
            key = f"{doc.source}:{doc.source_id}"
            node = (
                await session.execute(
                    select(Node).where(Node.properties["canonical_key"].astext == key)
                )
            ).scalar_one_or_none()
            if node is not None:
                node.properties = {**(node.properties or {}), "published_date": str(d)}
                flag_modified(node, "properties")
                if node.effective_from is None:
                    node.effective_from = d
            fixed += 1
            if fixed % 100 == 0:
                await session.commit()
                print(f"  … {fixed} dated")
        await session.commit()
    await engine.dispose()
    print(f"DONE: dated {fixed}, undatable {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
