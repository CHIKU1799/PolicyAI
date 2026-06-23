"""RBI notifications scraper (https://www.rbi.org.in/Scripts/NotificationUser.aspx).

The notifications page renders a table of circulars: each row has a date, a title
linking to NotificationUser.aspx?Id=NNNN, and a department. Selectors are kept at
the top so they are easy to re-tune when RBI changes its markup.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from playwright.async_api import Page

from policyai_scrapers.base import BaseScraper, DocMeta

ROW_SELECTOR = "table.tablebg tr, table#t"  # tuned against RBI's listing table
LINK_SELECTOR = "a[href*='NotificationUser.aspx?Id=']"
CONTENT_SELECTOR = "#pageContent, .tablecontent, td.tablecontent2"
ID_RE = re.compile(r"Id=(\d+)", re.IGNORECASE)


class RBIScraper(BaseScraper):
    scraper_kind = "rbi_notifications"
    regulator_key = "rbi"

    async def discover(self, page: Page) -> list[DocMeta]:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        metas: list[DocMeta] = []
        seen: set[str] = set()
        for link in await page.query_selector_all(LINK_SELECTOR):
            href = await link.get_attribute("href")
            title = (await link.inner_text()).strip()
            if not href or not title:
                continue
            url = urljoin(self.base_url, href)
            m = ID_RE.search(href)
            source_id = m.group(1) if m else url
            if source_id in seen:
                continue
            seen.add(source_id)
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=source_id,
                    source_url=url,
                    title=title,
                    published_date=await self._row_date(link),
                )
            )
        return metas

    async def _row_date(self, link) -> datetime.date | None:  # noqa: F821
        # The date sits in a sibling cell of the same row; best-effort parse.
        row = await link.evaluate_handle("el => el.closest('tr')")
        try:
            text = await row.evaluate("el => el.innerText")
        except Exception:  # noqa: BLE001
            return None
        for fmt in ("%b %d, %Y", "%d %b %Y", "%d-%m-%Y", "%b %d,%Y"):
            for token in re.findall(
                r"[A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4}|\d{1,2}-\d{1,2}-\d{4}", text
            ):
                try:
                    return datetime.strptime(token.replace(",", ", ").strip(), fmt).date()
                except ValueError:
                    continue
        return None

    async def fetch(self, page: Page, meta: DocMeta) -> str:
        await page.goto(meta.source_url, wait_until="domcontentloaded", timeout=60_000)
        for sel in CONTENT_SELECTOR.split(", "):
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    return text
        return (await page.inner_text("body")).strip()
