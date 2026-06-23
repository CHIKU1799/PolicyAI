"""IRDAI circulars scraper (https://irdai.gov.in/circulars).

IRDAI lists circulars with links to detail pages or attached PDFs. We capture the
detail-page text; PDF-only entries fall through to the body text and can be
flagged for OCR downstream if empty.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from playwright.async_api import Page

from policyai_scrapers.base import BaseScraper, DocMeta
from policyai_scrapers.sebi import _parse_any_date, _row_text

# Tuned against the live IRDAI listing (2026-06): each entry links to a
# /document-detail?documentId=NNN page; the human title is in the row, while the
# link text is just the bilingual word "परिपत्र / Circular".
LINK_SELECTOR = "a[href*='document-detail']"
CONTENT_SELECTOR = ".content, .field--name-body, article, main"


def _clean_title(row_text: str) -> str:
    t = " ".join(row_text.replace("Non-Archived", "").split())
    if " / " in t:  # bilingual "<Hindi> / <English>" -> keep the English half
        t = t.split(" / ")[-1].strip()
    return t


class IRDAIScraper(BaseScraper):
    scraper_kind = "irdai_circulars"
    regulator_key = "irdai"

    async def discover(self, page: Page) -> list[DocMeta]:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        metas: list[DocMeta] = []
        seen: set[str] = set()
        for link in await page.query_selector_all(LINK_SELECTOR):
            href = await link.get_attribute("href")
            if not href:
                continue
            url = urljoin(self.base_url, href)
            m = re.search(r"documentId=(\d+)", href)
            source_id = m.group(1) if m else url
            if source_id in seen:
                continue
            seen.add(source_id)
            row = await _row_text(link)
            title = _clean_title(row) or (await link.inner_text()).strip()
            if len(title) < 8:
                continue
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=source_id,
                    source_url=url,
                    title=title,
                    published_date=_parse_any_date(row),
                )
            )
        return metas

    async def fetch(self, page: Page, meta: DocMeta) -> str:
        await page.goto(meta.source_url, wait_until="domcontentloaded", timeout=60_000)
        for sel in CONTENT_SELECTOR.split(", "):
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        return (await page.inner_text("body")).strip()
