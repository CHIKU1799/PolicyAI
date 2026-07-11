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
TITLE_SELECTOR = "#pageContent b, .tableheader, .page-heading, h1"
ID_RE = re.compile(r"Id=(\d+)", re.IGNORECASE)
DATE_RE = re.compile(r"[A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4}|\d{1,2}-\d{1,2}-\d{4}")
# How far back to enumerate ids when a deep crawl gives no explicit from_id.
DEFAULT_DEEP_SPAN = 300


class RBIScraper(BaseScraper):
    scraper_kind = "rbi_notifications"
    regulator_key = "rbi"

    async def discover(self, page: Page) -> list[DocMeta]:
        """Recent-listing scrape (cadence crawls) or, in deep mode, an enumeration of
        the notification id range. RBI notifications are addressable by a sequential
        integer id (``NotificationUser.aspx?Id=NNNN``), so a deep backfill just walks
        ids [from_id, to_id]; the watermark drops ids we already have before any fetch.
        This reaches history the JS-only archive links can't, and the id-addressable
        HTML page carries the full text even for docs whose PDF CDN is bot-walled."""
        if self.deep:
            return await self._discover_id_range(page)
        return await self._discover_listing(page)

    async def _discover_id_range(self, page: Page) -> list[DocMeta]:
        hi = self.to_id or await self._max_listing_id(page)
        lo = self.from_id if self.from_id is not None else hi - DEFAULT_DEEP_SPAN
        lo, hi = min(lo, hi), max(lo, hi)
        return [
            DocMeta(
                source=self.regulator_key,
                source_id=str(i),
                source_url=f"{self.base_url}?Id={i}&Mode=0",
                title="",  # enriched from the detail page in fetch()
            )
            for i in range(lo, hi + 1)
        ]

    async def _max_listing_id(self, page: Page) -> int:
        """Highest notification id currently on the listing — the top of the range."""
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        ids: list[int] = []
        for link in await page.query_selector_all(LINK_SELECTOR):
            href = await link.get_attribute("href") or ""
            m = ID_RE.search(href)
            if m:
                ids.append(int(m.group(1)))
        if not ids:
            raise RuntimeError("RBI listing exposed no notification ids; markup may have changed")
        return max(ids)

    async def _discover_listing(self, page: Page) -> list[DocMeta]:
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
        text = ""
        for sel in CONTENT_SELECTOR.split(", "):
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    break
        if not text:
            text = (await page.inner_text("body")).strip()

        # In deep (id-enumeration) mode there is no listing row to read, so the id may
        # not correspond to a real notification and the title/date are unknown. Detect
        # the "no record" placeholder and enrich metadata off the detail page itself.
        if self.deep:
            if _is_empty_notice(text):
                return ""  # collect() drops docs with empty text
            if not meta.title:
                meta.title = await self._detail_title(page, text)
            if meta.published_date is None:
                meta.published_date = _first_date(text)
        return text

    async def _detail_title(self, page: Page, text: str) -> str:
        """Best-effort title for an id-enumerated notification: a heading element if
        present, else the first substantive line of the body."""
        for sel in TITLE_SELECTOR.split(", "):
            el = await page.query_selector(sel)
            if el:
                t = (await el.inner_text()).strip()
                if _looks_like_title(t):
                    return t
        for line in text.splitlines():
            line = line.strip()
            if _looks_like_title(line):
                return line[:300]
        return f"RBI Notification {page.url.rsplit('Id=', 1)[-1].split('&')[0]}"


# A notification detail page peppers non-title bold/heading text around the real
# title: file-size labels on the PDF link ("(336 kb)"), format tags, bare dates.
# Reject those so the id-enumerated doc gets a meaningful title, not "(336 kb)".
_TITLE_JUNK_RE = re.compile(
    r"^\(?\s*\d+(\.\d+)?\s*(kb|mb|gb)\s*\)?$|^(pdf|download|click here|back)$",
    re.IGNORECASE,
)


def _looks_like_title(text: str) -> bool:
    text = text.strip()
    if not (12 <= len(text) <= 300):
        return False
    if DATE_RE.fullmatch(text) or _TITLE_JUNK_RE.match(text):
        return False
    return any(c.isalpha() for c in text)


# "No record" / gap ids render a short placeholder rather than a 404. Treat a page
# whose body is tiny or matches a known empty-notice phrase as a non-document.
_EMPTY_MARKERS = ("no record", "no data", "does not exist", "not found", "page not found")


def _is_empty_notice(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 200:
        return True
    low = stripped.lower()
    return any(marker in low for marker in _EMPTY_MARKERS) and len(stripped) < 600


def _first_date(text: str) -> datetime.date | None:  # noqa: F821
    for token in DATE_RE.findall(text[:1200]):
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d-%m-%Y", "%b %d,%Y"):
            try:
                return datetime.strptime(token.replace(",", ", ").strip(), fmt).date()
            except ValueError:
                continue
    return None
