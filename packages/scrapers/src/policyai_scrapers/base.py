"""Base scraper abstractions for the monitoring agent.

Each regulator has a concrete subclass that knows how to (a) ``discover`` the list
of recent documents on its site and (b) ``fetch`` the full text of one document.
The runner handles dedup, persistence, and extraction — scrapers only produce
``DocMeta`` and text.

Sites are brittle: be polite (delays), tolerate per-document failures, and keep
selectors in one place so they are easy to re-tune when a site changes.
"""

from __future__ import annotations

import abc
import asyncio
import contextlib
import hashlib
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import date

from playwright.async_api import Page, async_playwright

from policyai_scrapers.util import log, select_new, with_retry

REQUEST_DELAY = float(os.getenv("SCRAPER_REQUEST_DELAY", "2.0"))
FETCH_ATTEMPTS = int(os.getenv("SCRAPER_FETCH_ATTEMPTS", "3"))


@dataclass
class DocMeta:
    """A discovered document, before its full text is fetched."""

    source: str  # regulator canonical_key, e.g. "rbi"
    source_id: str  # stable per-source id (doc number or canonical URL)
    source_url: str
    title: str
    published_date: date | None = None
    raw_text: str = field(default="")

    def content_hash(self) -> str:
        """Hash over the fields that define "changed". Title + text so an edited
        circular is re-ingested but an unchanged one is skipped."""
        h = hashlib.sha256()
        h.update(self.title.encode("utf-8"))
        h.update(self.raw_text.encode("utf-8"))
        return h.hexdigest()


class BaseScraper(abc.ABC):
    """One scraper per ``scraper_kind``. Subclasses set the class attributes and
    implement ``discover`` and ``fetch``."""

    scraper_kind: str
    regulator_key: str

    def __init__(
        self,
        base_url: str,
        *,
        backfill_months: int = 6,
        deep: bool = False,
        max_pages: int = 1,
        from_id: int | None = None,
        to_id: int | None = None,
    ) -> None:
        self.base_url = base_url
        self.backfill_months = backfill_months
        # Deep/backfill knobs. Default off so cadence crawls keep their cheap
        # "current listing only" behaviour; the backfill CLI turns these on to walk
        # historical archives (SEBI pagination) or an id range (RBI enumeration).
        self.deep = deep
        self.max_pages = max_pages
        self.from_id = from_id
        self.to_id = to_id
        self.discovered_count = 0  # set during collect() for ScanRun observability

    @abc.abstractmethod
    async def discover(self, page: Page) -> list[DocMeta]:
        """Return recent documents (without ``raw_text``)."""

    @abc.abstractmethod
    async def fetch(self, page: Page, meta: DocMeta) -> str:
        """Return the full text of one document."""

    @contextlib.asynccontextmanager
    async def _page(self) -> AsyncIterator[Page]:
        """Yield a fresh headless page, closing the browser afterwards. One place
        for the browser/user-agent boilerplate shared by collect() and discover_new()."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (compatible; PolicyAI-ComplianceMonitor/1.0; "
                    "+https://policyai.example/bot)"
                )
            )
            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()
                await browser.close()

    async def discover_new(self, known_ids: set[str] | None = None) -> list[DocMeta]:
        """Discover documents and apply the watermark, but do NOT fetch full text.

        This is the cheap half of a crawl — a network-only listing/enumeration pass
        with zero LLM cost — used by the backfill dry-run to report how many new
        documents are reachable before committing to fetch + extract them."""
        async with self._page() as page:
            discovered = await self.discover(page)
            self.discovered_count = len(discovered)
            fresh = select_new(discovered, known_ids)
        log.info(
            "%s: discovered %d, %d new (no fetch)",
            self.scraper_kind,
            self.discovered_count,
            len(fresh),
        )
        return fresh

    async def collect(self, known_ids: set[str] | None = None) -> list[DocMeta]:
        """Discover, drop already-ingested documents (the incremental watermark), then
        fetch each remaining doc's text. Per-document fetch failures are skipped."""
        fresh = await self.discover_new(known_ids)
        return await self.fetch_metas(fresh)

    async def fetch_metas(self, metas: list[DocMeta]) -> list[DocMeta]:
        """Fetch full text for already-discovered metas, with retry/backoff. Empty or
        failed fetches are dropped. ``fetch()`` may enrich title/date off the detail
        page, so the returned metas carry whatever it set."""
        results: list[DocMeta] = []
        if not metas:
            return results
        async with self._page() as page:
            for meta in metas:
                try:
                    await asyncio.sleep(REQUEST_DELAY)
                    meta.raw_text = await with_retry(
                        lambda m=meta: self.fetch(page, m),
                        attempts=FETCH_ATTEMPTS,
                        label=f"{self.scraper_kind}:{meta.source_id}",
                    )
                    if meta.raw_text.strip():
                        results.append(meta)
                except Exception as exc:  # noqa: BLE001 - one bad doc shouldn't kill the run
                    log.warning(
                        "%s: fetch failed for %s: %s", self.scraper_kind, meta.source_url, exc
                    )
        return results
