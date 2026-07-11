"""Monitoring runner: one pass over all enabled sources.

For each source whose cadence is due: crawl -> dedup against RawDocument
(content_hash) -> persist new docs -> extract each into the graph -> record a
ScanRun. Per-source failures are isolated so one bad regulator site doesn't abort
the whole pass. Invoked by the Render cron job:  python -m policyai_scrapers.runner
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

from policyai_extraction import notifications, storage
from policyai_extraction.llm import LLMClient
from policyai_extraction.map_all import map_unmapped_in_session
from policyai_extraction.pipeline import process_document
from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import RawDocument
from policyai_graph.models_app import (
    Alert,
    AlertKind,
    MonitoringSource,
    ScanRun,
    ScanStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_scrapers import SCRAPER_REGISTRY
from policyai_scrapers.util import log


def _is_due(source: MonitoringSource, now: datetime) -> bool:
    if not source.enabled:
        return False
    if source.last_scanned_at is None:
        return True
    return now - source.last_scanned_at >= timedelta(hours=source.cadence_hours)


async def _existing_ids(session: AsyncSession, source: str) -> dict[str, str]:
    """source_id -> content_hash for already-ingested docs of this source."""
    rows = await session.execute(
        select(RawDocument.source_id, RawDocument.content_hash).where(RawDocument.source == source)
    )
    return {sid: h for sid, h in rows.all()}


async def scan_source(session: AsyncSession, source: MonitoringSource, llm: LLMClient) -> ScanRun:
    run = ScanRun(source_id=source.id, status=ScanStatus.RUNNING.value)
    session.add(run)
    await session.flush()

    scraper_cls = SCRAPER_REGISTRY.get(source.scraper_kind)
    if scraper_cls is None:
        run.status = ScanStatus.FAILED.value
        run.error = f"No scraper for kind {source.scraper_kind!r}"
        run.finished_at = datetime.now(UTC)
        return run

    try:
        # Compute the watermark first so the scraper can skip fetching full text for
        # documents we already have — the crawl pays only for genuinely new ones.
        seen = await _existing_ids(session, source.regulator_key)
        scraper = scraper_cls(source.base_url)
        metas = await scraper.collect(known_ids=set(seen))
        # discovered_count is the total seen on the listing/feed; metas are the new
        # ones whose text we actually fetched.
        run.docs_found = scraper.discovered_count or len(metas)

        new_docs: list[RawDocument] = []
        for meta in metas:
            # Defence in depth: the watermark already filtered known source_ids, but
            # re-check in case a doc was ingested by a concurrent run mid-crawl.
            if meta.source_id in seen:
                continue
            doc = RawDocument(
                source=meta.source,
                source_id=meta.source_id,
                source_url=meta.source_url,
                title=meta.title,
                raw_text=meta.raw_text,
                published_date=meta.published_date,
                content_hash=meta.content_hash(),
            )
            session.add(doc)
            new_docs.append(doc)
        run.docs_new = len(new_docs)
        # Persist the raw documents (and scan-run progress) up front so a later
        # extraction failure can't lose them.
        await session.commit()

        # Archive each new document to the object-storage lake (R2 by default when
        # enabled). Graceful: a storage outage must not fail the scan.
        if storage.archive_enabled():
            for doc in new_docs:
                try:
                    await storage.upload(
                        f"regulations/{doc.source}/{doc.source_id}.txt",
                        (doc.raw_text or "").encode("utf-8"),
                        content_type="text/plain; charset=utf-8",
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning("archive failed for %s:%s: %s", doc.source, doc.source_id, exc)

        # Extract each document in its own transaction — one failure (deadlock,
        # transient error) rolls back just that doc and the scan continues.
        for doc in new_docs:
            try:
                await process_document(session, doc, llm)
                await session.commit()
            except Exception as exc:  # noqa: BLE001 - one doc failing isn't fatal
                await session.rollback()
                log.warning("extraction failed for %s:%s: %s", doc.source, doc.source_id, exc)

        source.last_scanned_at = datetime.now(UTC)
        run.status = ScanStatus.SUCCEEDED.value
    except Exception as exc:  # noqa: BLE001 - isolate per-source crawl failures
        run.status = ScanStatus.FAILED.value
        run.error = str(exc)[:1000]
        fail_message = f"Scan failed for {source.name}: {exc}"
        session.add(Alert(kind=AlertKind.SCAN_FAILED.value, message=fail_message))
        await notifications.notify_alert(AlertKind.SCAN_FAILED.value, fail_message)
    finally:
        run.finished_at = datetime.now(UTC)
    return run


def _map_after_scan() -> bool:
    """Whether a crawl should also map new regulations to obligations. Default on:
    a compliance officer who clicks 'Scan now' expects obligations, not just raw
    regulations. Set MAP_AFTER_SCAN=false to keep crawl and mapping separate."""
    return os.getenv("MAP_AFTER_SCAN", "true").lower() not in ("false", "0", "no")


async def run_once(*, force: bool = False, map_after: bool | None = None) -> None:
    """Run one monitoring pass. ``force=True`` scans every enabled source regardless
    of cadence (used by the dashboard 'Scan now' button). When ``map_after`` (default
    from MAP_AFTER_SCAN), newly ingested regulations are mapped to obligations in the
    same pass, so the flow is end-to-end: crawl -> extract -> map -> obligations."""
    if map_after is None:
        map_after = _map_after_scan()
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    llm = LLMClient()
    now = datetime.now(UTC)
    async with sessionmaker() as session:
        sources = (await session.execute(select(MonitoringSource))).scalars().all()
        due = [s for s in sources if s.enabled and (force or _is_due(s, now))]
        log.info("%d/%d sources %s", len(due), len(sources), "forced" if force else "due")
        for source in due:
            run = await scan_source(session, source, llm)
            await session.commit()
            log.info(
                "%s: %s (%d new / %d found)",
                source.name,
                run.status,
                run.docs_new,
                run.docs_found,
            )
        if map_after:
            # Turn freshly ingested regulations into obligations/gaps/tasks. The
            # relevance gate skips regulations that don't apply to the org, so this
            # only spends on the ones that matter.
            mapped, skipped = await map_unmapped_in_session(session, llm)
            log.info("post-scan mapping: mapped=%d skipped=%d", mapped, skipped)
    log.info("LLM cost: %s", llm.cost.summary())
    await llm.aclose()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_once())
