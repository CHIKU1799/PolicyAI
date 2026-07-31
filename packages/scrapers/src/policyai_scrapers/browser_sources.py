"""Browser-rendered sources for the regulators whose feeds/endpoints block plain
HTTP (see the audit note in ``feeds.py``). Each class keeps the ``scraper_kind``
of the feed source it replaces, so re-enabling the existing ``monitoring_sources``
row activates the browser scraper without any DB schema churn.

Listing URLs verified live 2026-07 (see per-class notes). Parsing is regex over
the rendered HTML snapshot: these are static gov listings whose markup changes
rarely, and regex keeps the hooks dependency-free and fixture-testable.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlsplit

from playwright.async_api import Page

from policyai_scrapers.base import DocMeta
from policyai_scrapers.browser_base import (
    MAX_ITEMS,
    MAX_TEXT_CHARS,
    BrowserListScraper,
    clean_fragment,
    parse_listing_date,
)
from policyai_scrapers.util import log

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)


def _rows(body: str) -> list[str]:
    return _ROW_RE.findall(body)


class CERTInAdvisoriesScraper(BrowserListScraper):
    """CERT-In advisories. The site is a JS-challenge frameset for plain HTTP but
    renders fine in a real browser. ``base_url`` is the advisory year index
    (pageid=PUBADVLIST); discovery follows the newest year's link to the actual
    list (pageid=PUBADVLIST02&year=YYYY), where each advisory is an anchor with
    a VLCODE, followed by a "(July 22, 2026)" date row and a one-line summary."""

    scraper_kind = "certin_rss"
    regulator_key = "certin"
    fetch_kind = "html"  # advisory detail pages are HTML with the full text
    content_selectors = ("#print_content", "table.content", "body")

    _YEAR_LINK_RE = re.compile(r'href="\s*([^"]*PUBADVLIST02[^"]*year=\d{4})"', re.I)
    _ITEM_RE = re.compile(
        r'href="(?P<href>[^"]*VLCODE=(?P<code>CIAD-[\d-]+))"(?P<tail>.*?)'
        r'(?=href="[^"]*VLCODE=|\Z)',
        re.S | re.I,
    )
    _DATE_RE = re.compile(r"\(([A-Za-z]+\s+\d{1,2},\s*\d{4})\)")
    _SUMMARY_RE = re.compile(r'<span style="padding-left: 20px">(.*?)</span>', re.S | re.I)

    async def render_listing(self, page: Page) -> str:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        await self._settle(page)
        year_links = self._YEAR_LINK_RE.findall(await page.content())
        if not year_links:
            log.warning("%s: no advisory year links on %s", self.scraper_kind, self.base_url)
            return ""
        newest = urljoin(self.base_url, year_links[0].replace("&amp;", "&").strip())
        await page.goto(newest, wait_until="domcontentloaded", timeout=60_000)
        await self._settle(page)
        return await page.content()

    def parse_listing(self, body: str) -> list[DocMeta]:
        metas: list[DocMeta] = []
        for m in self._ITEM_RE.finditer(body):
            code = m.group("code")
            tail = m.group("tail")
            d = self._DATE_RE.search(tail)
            s = self._SUMMARY_RE.search(tail)
            summary = clean_fragment(s.group(1)) if s else ""
            title = f"CERT-In Advisory {code}"
            if summary:
                title = f"{title}: {summary}"
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=code,
                    source_url=urljoin(self.base_url, m.group("href").replace("&amp;", "&")),
                    title=title,
                    published_date=parse_listing_date(d.group(1)) if d else None,
                )
            )
        return metas


class NPCICircularsScraper(BrowserListScraper):
    """NPCI circulars/OCs. The React page and its Strapi-style JSON API both sit
    behind an Akamai WAF that 403s non-browser clients, so discovery first renders
    the listing (which mints the WAF cookies), then calls the page's own
    /api/circulars/<product> endpoint through the browser context. The API gives
    stable ids, titles and PDF urls; items carry only a fiscal-year label, so
    published_date stays None and the ingest date stands in for recency."""

    scraper_kind = "npci_rss"
    regulator_key = "npci"
    fetch_kind = "pdf"
    ready_selector = "ul.circulars-body li"
    ready_timeout_ms = 30_000

    async def render_listing(self, page: Page) -> str:
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
        await self._settle(page)
        parts = urlsplit(self.base_url)
        product = parts.path.rstrip("/").rsplit("/", 1)[-1]
        origin = f"{parts.scheme}://{parts.netloc}"
        files: list[dict] = []
        year = datetime.now().year
        for y in (year, year - 1):  # current + previous year keeps year-boundary runs non-empty
            api = (
                f"{origin}/api/circulars/{product}"
                f"?pageNum=1&year={y}&sort=desc&size={MAX_ITEMS}&locale=en"
            )
            # The WAF fingerprints more than cookies, so an out-of-page request
            # 403s; fetching from inside the rendered page passes as the page's
            # own XHR (which is exactly what it is).
            try:
                raw = await page.evaluate(
                    "url => fetch(url, {headers: {accept: 'application/json'}})"
                    ".then(r => r.ok ? r.text() : '')",
                    api,
                )
                payload = json.loads(raw or "{}")
            except Exception:  # noqa: BLE001 - WAF challenge page instead of JSON
                log.warning("%s: API fetch failed for %s", self.scraper_kind, api)
                continue
            files.extend((payload.get("data") or {}).get("files") or [])
        return json.dumps({"files": files})

    async def fetch(self, page: Page, meta: DocMeta) -> str:
        """The uploads CDN 403s any request that is not the page's own, so park
        the page on the listing once per session and fetch the PDF in-page. NPCI
        circulars are scanned image PDFs with no text layer; the shared
        ``pdf_bytes_to_text`` OCR fallback recovers their text. If even that
        fails, fall back to the title (as the MCA scraper does) so the document
        is still recorded."""
        parts = urlsplit(self.base_url)
        if urlsplit(page.url).netloc != parts.netloc:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(self.settle_ms)
        try:
            text = (await self._pdf_text_in_page(page, meta.source_url))[:MAX_TEXT_CHARS]
        except Exception as exc:  # noqa: BLE001 - WAF challenge instead of the PDF
            log.warning("%s: pdf fetch failed for %s: %s", self.scraper_kind, meta.source_url, exc)
            text = ""
        return text or meta.title

    def parse_listing(self, body: str) -> list[DocMeta]:
        parts = urlsplit(self.base_url)
        origin = f"{parts.scheme}://{parts.netloc}"
        metas: list[DocMeta] = []
        try:
            files = json.loads(body or "{}").get("files") or []
        except json.JSONDecodeError:
            return metas
        for f in files:
            media = f.get("media") or {}
            url, title = media.get("url"), (f.get("fileName") or "").strip()
            if not url or not title or f.get("id") is None:
                continue  # entries without an attached PDF are placeholders
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=str(f["id"]),
                    source_url=urljoin(origin, url),
                    title=clean_fragment(title),
                )
            )
        return metas


class PFRDACircularsScraper(BrowserListScraper):
    """PFRDA active circulars on the Liferay site: div.basic-card entries with an
    h2 title, a Ref number and an Issue Date. Detail pages are HTML wrappers, so
    the base class's thin-page PDF fallback pulls the attached circular when the
    wrapper carries little text."""

    scraper_kind = "pfrda_rss"
    regulator_key = "pfrda"
    fetch_kind = "html"
    ready_selector = "div.basic-card"
    content_selectors = (".journal-content-article", "article", ".portlet-body", "main")
    # Detail pages are ~2k chars of site chrome around a PDF attachment that
    # carries the actual circular text, so push the threshold up to prefer the PDF.
    min_detail_chars = 3_000

    _CARD_RE = re.compile(
        r'<div class="basic-card">\s*<a href="(?P<href>[^"]+)"(?P<card>.*?)</a>',
        re.S | re.I,
    )
    _TITLE_RE = re.compile(r'<h2 class="basic-title">(?P<t>.*?)</h2>', re.S | re.I)
    _DATE_RE = re.compile(r"<strong>\s*Issue Date:\s*</strong>\s*(?P<d>[\d/-]+)", re.I)

    def parse_listing(self, body: str) -> list[DocMeta]:
        metas: list[DocMeta] = []
        for m in self._CARD_RE.finditer(body):
            t = self._TITLE_RE.search(m.group("card"))
            if not t:
                continue
            url = urljoin(self.base_url, m.group("href").replace("&amp;", "&"))
            slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
            d = self._DATE_RE.search(m.group("card"))
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=slug,
                    source_url=url.split("?", 1)[0],  # drop the back-url tracking params
                    title=clean_fragment(t.group("t")),
                    published_date=parse_listing_date(d.group("d")) if d else None,
                )
            )
        return metas


class IFSCACircularsScraper(BrowserListScraper):
    """IFSCA circulars: a DataTables listing whose rows carry a publish date, a
    title and a /CommonDirect/GetFileView link. GetFileView is an HTML viewer
    page; the raw PDF sits behind the same query on /CommonDirect/ViewFile (the
    viewer's iframe src), so the URL is rewritten at parse time. The file id is
    the stable per-document identifier."""

    scraper_kind = "ifsca_rss"
    regulator_key = "ifsca"
    fetch_kind = "pdf"
    ready_selector = "td.PublishDate, td[data-label='Date']"

    _CELLS_RE = re.compile(
        r"PublishDate[^>]*>(?P<date>[^<]+)</td>\s*"
        r"<td[^>]*Title[^>]*>(?P<title>.*?)</td>.*?"
        r'href="(?P<href>[^"]*GetFileView[^"]*)"',
        re.S | re.I,
    )

    def parse_listing(self, body: str) -> list[DocMeta]:
        metas: list[DocMeta] = []
        for row in _rows(body):
            m = self._CELLS_RE.search(row)
            if not m:
                continue
            href = m.group("href").replace("&amp;", "&")
            url = urljoin(self.base_url, href).replace("/GetFileView", "/ViewFile")
            file_id = (parse_qs(urlsplit(url).query).get("id") or [url])[0]
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=file_id,
                    source_url=url,
                    title=clean_fragment(m.group("title")),
                    published_date=parse_listing_date(m.group("date")),
                )
            )
        return metas


class FIUComplianceOrdersScraper(BrowserListScraper):
    """FIU-IND compliance orders (Section 13 PMLA actions): a plain table of
    serial no / date / title / size / PDF link. The site serves a JS challenge to
    non-browser clients but renders directly in Playwright."""

    scraper_kind = "fiu_rss"
    regulator_key = "fiu_ind"
    fetch_kind = "pdf"

    _CELLS_RE = re.compile(
        r"<td[^>]*>\s*\d+\s*</td>\s*"
        r"<td[^>]*>(?P<date>[^<]+)</td>\s*"
        r"<td[^>]*>(?P<title>.*?)</td>\s*"
        r"<td[^>]*>[^<]*</td>\s*"
        r'<td[^>]*>\s*<a[^>]*href="(?P<href>[^"]+\.pdf)"',
        re.S | re.I,
    )

    def parse_listing(self, body: str) -> list[DocMeta]:
        metas: list[DocMeta] = []
        for row in _rows(body):
            m = self._CELLS_RE.search(row)
            if not m:
                continue
            url = urljoin(self.base_url, m.group("href"))
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=urlsplit(url).path.rsplit("/", 1)[-1],
                    source_url=url,
                    title=clean_fragment(m.group("title")),
                    published_date=parse_listing_date(m.group("date")),
                )
            )
        return metas


class DGFTNotificationsScraper(BrowserListScraper):
    """DGFT notifications: the CP portal renders a DataTable of notification no /
    year / description / date with a direct PDF link on content.dgft.gov.in. The
    /CP/?opt=rss feed emits junk XML, but the rendered listing is clean."""

    scraper_kind = "dgft_rss"
    regulator_key = "dgft"
    fetch_kind = "pdf"
    ready_selector = "a.attachmentBtn"

    _CELLS_RE = re.compile(
        r"<td[^>]*>\s*\d+\s*</td>\s*"
        r"<td[^>]*>(?P<num>[^<]+)</td>\s*"
        r"<td[^>]*>[^<]*</td>\s*"
        r"<td[^>]*>(?P<title>.*?)</td>\s*"
        r"<td[^>]*>(?P<date>[^<]+)</td>.*?"
        r'href="(?P<href>[^"]+)"',
        re.S | re.I,
    )
    _GUID_RE = re.compile(r"dgftprod/([0-9a-fA-F-]{36})")

    def parse_listing(self, body: str) -> list[DocMeta]:
        metas: list[DocMeta] = []
        for row in _rows(body):
            m = self._CELLS_RE.search(row)
            if not m:
                continue
            url = urljoin(self.base_url, m.group("href").strip()).replace(" ", "%20")
            guid = self._GUID_RE.search(url)
            num = clean_fragment(m.group("num"))
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=guid.group(1) if guid else url,
                    source_url=url,
                    title=f"Notification No. {num}: {clean_fragment(m.group('title'))}",
                    published_date=parse_listing_date(m.group("date")),
                )
            )
        return metas
