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
import hashlib
import os
from dataclasses import dataclass, field
from datetime import date

from playwright.async_api import Page, async_playwright

REQUEST_DELAY = float(os.getenv("SCRAPER_REQUEST_DELAY", "2.0"))


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

    def __init__(self, base_url: str, *, backfill_months: int = 6) -> None:
        self.base_url = base_url
        self.backfill_months = backfill_months

    @abc.abstractmethod
    async def discover(self, page: Page) -> list[DocMeta]:
        """Return recent documents (without ``raw_text``)."""

    @abc.abstractmethod
    async def fetch(self, page: Page, meta: DocMeta) -> str:
        """Return the full text of one document."""

    async def collect(self) -> list[DocMeta]:
        """Drive a headless browser end-to-end: discover, then fetch each doc's
        text. Per-document fetch failures are skipped, not fatal."""
        results: list[DocMeta] = []
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
                metas = await self.discover(page)
                for meta in metas:
                    try:
                        await asyncio.sleep(REQUEST_DELAY)
                        meta.raw_text = await self.fetch(page, meta)
                        if meta.raw_text.strip():
                            results.append(meta)
                    except Exception as exc:  # noqa: BLE001 - one bad doc shouldn't kill the run
                        print(f"[{self.scraper_kind}] fetch failed for {meta.source_url}: {exc}")
            finally:
                await context.close()
                await browser.close()
        return results
