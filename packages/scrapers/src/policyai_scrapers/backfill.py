"""Deep historical backfill for the HTML crawlers (RBI, SEBI).

The cadence runner (``policyai_scrapers.runner``) only scrapes each regulator's
*current* listing page — cheap, and right for "what changed since yesterday". This
CLI is the other axis: reach *backwards* into the archive to make the corpus deep
enough that the gap engine can flag fine-grained compliance issues.

Two site-specific strategies (see the scrapers):

* **RBI** — notifications are addressable by a sequential integer id
  (``NotificationUser.aspx?Id=NNNN``). A deep crawl enumerates the id range and lets
  the watermark drop ids already ingested, so it fetches only genuine gaps. The
  id-addressable HTML page carries full text even for docs whose PDF CDN is walled,
  which is why this also backfills the Drive-blocked ids without any Drive re-auth.
* **SEBI** — circulars are slug-addressed with JS pagination; a deep crawl pages
  through the listing up to ``--sebi-pages``.

Discovery and fetch are decoupled so ``--dry-run`` reports how many new documents are
reachable with **zero LLM spend** before you commit to fetch + extract them. The real
run reuses ``policyai_extraction.ingest`` end-to-end (dedup, per-doc retry, mapping,
cost tracking), so a backfilled document is indistinguishable from a crawled one.

CLI:
    python -m policyai_scrapers.backfill --regulator rbi --dry-run
    python -m policyai_scrapers.backfill --regulator rbi --from-id 13373 --limit 50 --map
    python -m policyai_scrapers.backfill --regulator sebi --sebi-pages 6 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from policyai_extraction.ingest import ingest_records
from policyai_extraction.llm import LLMClient
from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import RawDocument
from policyai_graph.models_app import MonitoringSource
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_scrapers import SCRAPER_REGISTRY
from policyai_scrapers.base import DocMeta
from policyai_scrapers.util import log

# regulator flag -> the scraper_kind whose seeded MonitoringSource base_url we reuse.
_KIND_FOR = {"rbi": "rbi_notifications", "sebi": "sebi_circulars"}


async def _known_ids(session: AsyncSession, source: str) -> set[str]:
    rows = await session.execute(select(RawDocument.source_id).where(RawDocument.source == source))
    return set(rows.scalars().all())


async def _base_url(session: AsyncSession, scraper_kind: str) -> str:
    row = await session.execute(
        select(MonitoringSource.base_url).where(MonitoringSource.scraper_kind == scraper_kind)
    )
    url = row.scalars().first()
    if not url:
        raise SystemExit(f"No MonitoringSource seeded for scraper_kind={scraper_kind!r}")
    return url


def _record(meta: DocMeta) -> dict:
    return {
        "source": meta.source,
        "source_id": meta.source_id,
        "source_url": meta.source_url,
        "title": meta.title,
        "raw_text": meta.raw_text,
        "published_date": meta.published_date.isoformat() if meta.published_date else None,
    }


async def _run(
    *,
    regulator: str,
    from_id: int | None,
    to_id: int | None,
    sebi_pages: int,
    limit: int | None,
    dry_run: bool,
    do_map: bool,
) -> int:
    scraper_kind = _KIND_FOR[regulator]
    scraper_cls = SCRAPER_REGISTRY[scraper_kind]
    engine = make_engine()
    sm = make_sessionmaker(engine)
    llm = LLMClient()
    try:
        async with sm() as session:
            known = await _known_ids(session, regulator)
            base_url = await _base_url(session, scraper_kind)
            scraper = scraper_cls(
                base_url,
                deep=True,
                max_pages=sebi_pages,
                from_id=from_id,
                to_id=to_id,
            )
            # Cheap half: discover + watermark, no full-text fetch, no LLM cost.
            fresh = await scraper.discover_new(known)
            log.info(
                "backfill %s: %d already ingested, %d new reachable",
                regulator,
                len(known),
                len(fresh),
            )
            if limit:
                fresh = fresh[:limit]
                log.info("backfill %s: capped to %d this run (--limit)", regulator, len(fresh))
            if dry_run:
                print(
                    f"[dry-run] {regulator}: {len(known)} ingested, "
                    f"{len(fresh)} new reachable (would fetch+extract these)"
                )
                return 0
            if not fresh:
                print(f"{regulator}: nothing new to backfill")
                return 0

            # Expensive half: fetch full text (network), then extract + map (LLM).
            fetched = await scraper.fetch_metas(fresh)
            log.info("backfill %s: fetched text for %d/%d", regulator, len(fetched), len(fresh))
            records = [_record(m) for m in fetched]
            result = await ingest_records(session, records, llm)
            if do_map and result.extracted:
                from policyai_extraction.map_all import map_unmapped_in_session

                mapped, skipped = await map_unmapped_in_session(session, llm)
                log.info("post-backfill mapping: mapped=%d skipped=%d", mapped, skipped)
            print(f"{regulator}: {result.summary()}")
            log.info("LLM cost: %s", llm.cost.summary())
            for e in result.errors[:20]:
                print(f"  - {e}")
            return 0 if result.failed == 0 else 1
    finally:
        await llm.aclose()
        await engine.dispose()


def main() -> int:
    ap = argparse.ArgumentParser(description="Deep historical backfill for RBI/SEBI crawlers.")
    ap.add_argument("--regulator", choices=sorted(_KIND_FOR), required=True)
    ap.add_argument("--from-id", type=int, default=None, help="RBI: lowest notification id")
    ap.add_argument("--to-id", type=int, default=None, help="RBI: highest id (default listing max)")
    ap.add_argument("--sebi-pages", type=int, default=5, help="SEBI: max listing pages to walk")
    ap.add_argument("--limit", type=int, default=None, help="cap docs fetched+extracted this run")
    ap.add_argument("--dry-run", action="store_true", help="report reachable counts, no spend")
    ap.add_argument("--map", action="store_true", dest="do_map", help="map new regs to obligations")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return asyncio.run(
        _run(
            regulator=args.regulator,
            from_id=args.from_id,
            to_id=args.to_id,
            sebi_pages=args.sebi_pages,
            limit=args.limit,
            dry_run=args.dry_run,
            do_map=args.do_map,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
