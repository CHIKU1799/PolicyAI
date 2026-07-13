"""Manual document ingestion — feed pre-fetched regulation text into the pipeline.

The crawlers (``policyai_scrapers``) are one way documents enter the graph; this is
the other. Given records of already-fetched text (e.g. RBI notification PDFs pulled
from a Drive folder, or any text extracted off-platform), it creates ``RawDocument``
rows and runs each through the same ``process_document`` extraction pipeline the
crawler uses — so a hand-fed document and a crawled one are indistinguishable once
in the graph.

Dedup is on ``(source, source_id)`` so re-running is safe and idempotent. Each
document extracts in its own transaction, so one failure never aborts the batch.

CLI:
    python -m policyai_extraction.ingest <records.jsonl> [--limit N] [--dry-run]

Each JSONL line is a record:
    {"source": "rbi", "source_id": "12781",
     "source_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12781",
     "title": "...", "raw_text": "...", "published_date": "2026-03-14"}
``published_date`` is optional (ISO date); ``raw_text`` is required.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models import RawDocument
from policyai_graph.models_app import DEFAULT_ORG_ID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction.dbretry import MAX_ATTEMPTS, is_transient
from policyai_extraction.llm import LLMClient
from policyai_extraction.pipeline import process_document

log = logging.getLogger("policyai.ingest")


@dataclass
class IngestResult:
    created: int = 0
    extracted: int = 0
    skipped_existing: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"{self.created} new docs, {self.extracted} extracted, "
            f"{self.skipped_existing} already present, {self.failed} failed"
        )


def _content_hash(title: str, text: str) -> str:
    h = hashlib.sha256()
    h.update((title or "").encode("utf-8"))
    h.update((text or "").encode("utf-8"))
    return h.hexdigest()


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


async def _existing_ids(session: AsyncSession, source: str) -> set[str]:
    rows = await session.execute(select(RawDocument.source_id).where(RawDocument.source == source))
    return set(rows.scalars().all())


async def ingest_records(
    session: AsyncSession,
    records: Iterable[dict],
    llm: LLMClient,
    *,
    org_id=DEFAULT_ORG_ID,
    dry_run: bool = False,
    limit: int | None = None,
) -> IngestResult:
    """Ingest pre-fetched documents. Caller provides an open session; we commit
    per document so a mid-batch failure keeps everything already done."""
    result = IngestResult()
    records = list(records)

    # Dedup against what's already ingested, per source, up front.
    by_source: dict[str, set[str]] = {}
    for rec in records:
        src = rec.get("source", "")
        if src not in by_source:
            by_source[src] = await _existing_ids(session, src)

    for rec in records:
        source = rec.get("source", "")
        source_id = str(rec.get("source_id", "")).strip()
        text = (rec.get("raw_text") or "").strip()
        if not source or not source_id or not text:
            result.failed += 1
            result.errors.append(f"missing source/source_id/raw_text: {source}:{source_id}")
            continue
        if source_id in by_source.get(source, set()):
            result.skipped_existing += 1
            continue
        if limit and result.created >= limit:
            break
        if dry_run:
            result.created += 1
            continue

        # Retry the doc on transient pooler drops (a dropped connection would
        # otherwise silently lose the document); give up only on a real error or
        # after exhausting retries.
        for attempt in range(1, MAX_ATTEMPTS + 1):
            doc = RawDocument(
                source=source,
                source_id=source_id,
                source_url=rec.get("source_url") or "",
                title=rec.get("title") or f"{source}:{source_id}",
                raw_text=text,
                published_date=_parse_date(rec.get("published_date")),
                content_hash=_content_hash(rec.get("title") or "", text),
            )
            session.add(doc)
            try:
                await session.flush()
                await process_document(session, doc, llm, org_id=org_id)
                await session.commit()
                result.created += 1
                result.extracted += 1
                by_source[source].add(source_id)
                log.info("ingested %s:%s -> %s", source, source_id, doc.title[:60])
                break
            except Exception as exc:  # noqa: BLE001 - isolate per-doc failures
                try:
                    await session.rollback()
                except Exception:  # noqa: BLE001 - rollback on a dead conn can itself fail
                    pass
                if is_transient(exc) and attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(1.5 * attempt)
                    log.info(
                        "ingest retry %d/%d for %s:%s", attempt, MAX_ATTEMPTS, source, source_id
                    )
                    continue
                result.failed += 1
                result.errors.append(f"{source}:{source_id}: {str(exc)[:200]}")
                log.warning("ingest failed for %s:%s: %s", source, source_id, exc)
                break

    return result


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


async def _run(path: Path, *, limit: int | None, dry_run: bool, do_map: bool) -> IngestResult:
    # limit counts NEW documents, applied inside the loop, so resumable batch
    # runs make progress instead of re-scanning the same already-ingested prefix.
    records = _load_jsonl(path)
    engine = make_engine()
    sm = make_sessionmaker(engine)
    llm = LLMClient()
    try:
        async with sm() as session:
            result = await ingest_records(session, records, llm, dry_run=dry_run, limit=limit)
            if do_map and not dry_run and result.extracted:
                # End-to-end: turn the just-ingested regulations into obligations.
                from policyai_extraction.map_all import map_unmapped_in_session

                mapped, skipped = await map_unmapped_in_session(session, llm)
                log.info("post-ingest mapping: mapped=%d skipped=%d", mapped, skipped)
    finally:
        await llm.aclose()
        await engine.dispose()
    log.info("ingest done: %s", result.summary())
    if not dry_run:
        log.info("LLM cost: %s", llm.cost.summary())
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest pre-fetched documents into the graph.")
    ap.add_argument("jsonl", type=Path, help="JSONL file of document records")
    ap.add_argument("--limit", type=int, default=None, help="stop after N newly ingested documents")
    ap.add_argument("--dry-run", action="store_true", help="report counts without writing")
    ap.add_argument(
        "--map",
        action="store_true",
        dest="do_map",
        help="after ingesting, map new regulations to obligations (end-to-end)",
    )
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = asyncio.run(
        _run(args.jsonl, limit=args.limit, dry_run=args.dry_run, do_map=args.do_map)
    )
    print(result.summary())
    if result.errors:
        print("errors:")
        for e in result.errors[:20]:
            print(f"  - {e}")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
