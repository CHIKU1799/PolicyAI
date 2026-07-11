"""SEBI legal circulars scraper.

SEBI lists circulars in a table whose rows link to per-circular detail pages
under /legal/circulars/. Selectors at the top for easy re-tuning.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from playwright.async_api import Page

from policyai_scrapers.base import BaseScraper, DocMeta

# Tuned against the live SEBI legal listing (2026-06): circular + master-circular
# links live under /legal/ and contain "circular" in the path.
LINK_SELECTOR = "a[href*='/legal/'][href*='circular']"
CONTENT_SELECTOR = "#webApplicationDataDiv, .panel-body, #pdfData, article"


async def _row_text(link) -> str:
    try:
        row = await link.evaluate_handle("e => e.closest('tr') || e.parentElement")
        return await row.evaluate("e => e.innerText")
    except Exception:  # noqa: BLE001
        return ""


class SEBIScraper(BaseScraper):
    scraper_kind = "sebi_circulars"
    regulator_key = "sebi"

    async def discover(self, page: Page) -> list[DocMeta]:
        """Harvest circular links from the listing. In deep mode, page through the
        JS-driven pager (``searchFormNewsList('n','-1')`` = next) up to ``max_pages``
        so a backfill reaches older circulars, not just the first 25."""
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        metas: list[DocMeta] = []
        seen: set[str] = set()
        pages = self.max_pages if self.deep else 1
        for page_no in range(pages):
            if page_no > 0 and not await self._go_next(page):
                break  # no further pages
            await self._harvest(page, metas, seen)
        return metas

    async def _harvest(self, page: Page, metas: list[DocMeta], seen: set[str]) -> None:
        for link in await page.query_selector_all(LINK_SELECTOR):
            href = await link.get_attribute("href")
            title = (await link.inner_text()).strip()
            if not href or not title or len(title) < 8:
                continue
            url = urljoin(self.base_url, href)
            if url in seen:
                continue
            seen.add(url)
            # SEBI shows the date in the row ("Jun 03, 2026\tTitle"), not the title.
            published = _parse_any_date(await _row_text(link)) or _parse_any_date(title)
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=url.rstrip("/").rsplit("/", 1)[-1],
                    source_url=url,
                    title=title,
                    published_date=published,
                )
            )

    async def _go_next(self, page: Page) -> bool:
        """Advance the JS pager by one page; return False if it didn't move."""
        before = await self._first_href(page)
        try:
            await page.evaluate("searchFormNewsList('n','-1')")
        except Exception:  # noqa: BLE001 - pager JS absent / last page
            return False
        try:
            await page.wait_for_function(
                "(prev) => { const a = document.querySelector("
                "\"a[href*='/legal/'][href*='circular']\"); return a && a.href !== prev; }",
                arg=before,
                timeout=15_000,
            )
        except Exception:  # noqa: BLE001 - content didn't change => end of listing
            return False
        return True

    async def _first_href(self, page: Page) -> str:
        el = await page.query_selector(LINK_SELECTOR)
        return (await el.get_attribute("href")) if el else ""

    async def fetch(self, page: Page, meta: DocMeta) -> str:
        await page.goto(meta.source_url, wait_until="domcontentloaded", timeout=60_000)
        for sel in CONTENT_SELECTOR.split(", "):
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        return (await page.inner_text("body")).strip()


def _parse_any_date(text: str) -> datetime.date | None:  # noqa: F821
    for token in re.findall(r"[A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4}|\d{1,2}-\d{1,2}-\d{4}", text):
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(token.strip(), fmt).date()
            except ValueError:
                continue
    return None
