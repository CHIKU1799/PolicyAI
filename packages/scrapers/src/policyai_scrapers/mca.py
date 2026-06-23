"""MCA notifications scraper.

MCA publishes notifications/circulars largely as linked PDFs on its notifications
page. We capture the listing link text as the title and the detail/body text; PDF
-only entries produce little text and are flagged for OCR downstream.
"""

from __future__ import annotations

from urllib.parse import urljoin

from playwright.async_api import Page

from policyai_scrapers.base import BaseScraper, DocMeta
from policyai_scrapers.sebi import _parse_any_date

LINK_SELECTOR = "a[href$='.pdf'], a[href*='notification'], table a[href]"
CONTENT_SELECTOR = ".content, article, main, #bodyContent"


class MCAScraper(BaseScraper):
    scraper_kind = "mca_notifications"
    regulator_key = "mca"

    async def discover(self, page: Page) -> list[DocMeta]:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        metas: list[DocMeta] = []
        seen: set[str] = set()
        for link in await page.query_selector_all(LINK_SELECTOR):
            href = await link.get_attribute("href")
            title = (await link.inner_text()).strip()
            if not href or not title or len(title) < 8:
                continue
            url = urljoin(self.base_url, href)
            if url in seen:
                continue
            seen.add(url)
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=url.rsplit("/", 1)[-1] or url,
                    source_url=url,
                    title=title,
                    published_date=_parse_any_date(title),
                )
            )
        return metas

    async def fetch(self, page: Page, meta: DocMeta) -> str:
        if meta.source_url.lower().endswith(".pdf"):
            # PDF bytes aren't extracted here; the runner flags empty text. Return
            # the title so the record is still created and visible.
            return meta.title
        await page.goto(meta.source_url, wait_until="domcontentloaded", timeout=60_000)
        for sel in CONTENT_SELECTOR.split(", "):
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        return (await page.inner_text("body")).strip()
