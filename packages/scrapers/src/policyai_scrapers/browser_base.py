"""Browser-rendered listing scrapers for regulators whose endpoints block plain HTTP.

Several regulators (CERT-In, NPCI, PFRDA, IFSCA, FIU-IND, DGFT) either have no
RSS feed or bot-wall every non-browser client, so ``FeedScraper`` cannot reach
them. ``BrowserListScraper`` renders the listing page in Playwright with a
realistic desktop profile, snapshots the resulting HTML (or a JSON API body the
page itself is entitled to call), and hands it to a pure-Python ``parse_listing``
hook. Keeping the parse step browser-free means each source's row extraction is
unit-testable against a saved HTML fixture with no network or browser at all.

Full text comes from the item's own page: HTML detail pages are rendered in the
same browser context; PDF links are downloaded through the context's request
client (sharing its cookies, so WAF-issued tokens carry over) and text-extracted
with pypdf, mirroring how policy uploads are handled elsewhere in the platform.
Scanned PDFs with no usable text layer fall through to RapidOCR (see ``ocr.py``),
which is what unlocks NPCI and DGFT; ``OCR_ENABLED=0`` turns that fallback off.
"""

from __future__ import annotations

import abc
import contextlib
import io
import os
import re
from collections.abc import AsyncIterator
from datetime import date, datetime

from playwright.async_api import BrowserContext, Page, async_playwright

from policyai_scrapers.base import BaseScraper, DocMeta
from policyai_scrapers.util import log

# Realistic desktop profile: the NIC/Akamai WAFs in front of these sites 403 any
# UA that looks like a bot, even from a real browser engine.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1366, "height": 900}
NAV_TIMEOUT_MS = 60_000
# Cap discovery per run; the runner's cadence keeps the stream fresh, so a crawl
# never needs to walk deep history.
MAX_ITEMS = 30
MAX_TEXT_CHARS = 40_000

_WS_RE = re.compile(r"\s+")
_TAG_RE = re.compile(r"<[^>]+>")
# "December 30th 2025" -> "December 30 2025"
_ORDINAL_RE = re.compile(r"(\d{1,2})(st|nd|rd|th)\b", re.IGNORECASE)
_DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%Y-%m-%d",
)


def clean_fragment(html: str) -> str:
    """Tags stripped, entities unescaped, whitespace collapsed. For pulling a
    title or date out of one listing cell, not for whole documents."""
    text = _TAG_RE.sub(" ", html or "")
    for a, b in (
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", '"'),
        ("&#39;", "'"),
        ("&nbsp;", " "),
    ):
        text = text.replace(a, b)
    return _WS_RE.sub(" ", text).strip()


def parse_listing_date(value: str | None) -> date | None:
    """Best-effort date from the formats these listings actually use:
    21/07/2026 (IFSCA, DGFT), 14-07-2026 (PFRDA), July 22, 2026 (CERT-In),
    December 30th 2025 (FIU-IND)."""
    if not value:
        return None
    cleaned = _ORDINAL_RE.sub(r"\1", clean_fragment(value)).replace(",", ", ")
    cleaned = _WS_RE.sub(" ", cleaned).strip(" ()")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


# Below this, a "text layer" is really just page furniture (headers, page
# numbers) or nothing at all — treat the PDF as scanned and OCR it.
OCR_FALLBACK_CHARS = 200


def pdf_bytes_to_text(data: bytes) -> str:
    """Text of a PDF: the pypdf text layer (same approach as the policy-upload
    path), falling back to OCR for scanned PDFs whose layer is empty or trivial
    (NPCI and DGFT publish image-only scans). ``OCR_ENABLED=0`` disables the
    fallback and restores the pypdf-only behaviour."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    if len(text) >= OCR_FALLBACK_CHARS or os.getenv("OCR_ENABLED", "1") == "0":
        return text
    try:
        from policyai_scrapers.ocr import pdf_ocr_text

        ocr_text = pdf_ocr_text(data)
    except Exception as exc:  # noqa: BLE001 - keep whatever pypdf produced
        log.warning("pdf ocr fallback failed (%s); keeping pypdf text", exc)
        return text
    if len(ocr_text) > len(text):
        log.info("pdf text via ocr fallback (pypdf %d chars, ocr %d)", len(text), len(ocr_text))
        return ocr_text
    log.info("pdf text via pypdf (%d chars); ocr added nothing", len(text))
    return text


class BrowserListScraper(BaseScraper):
    """Playwright-rendered listing source. Subclasses set the class attributes
    and implement ``parse_listing`` (pure Python: rendered HTML/JSON -> DocMeta
    rows); sources with a multi-step listing flow also override ``render_listing``.
    """

    # CSS selector that signals the listing has hydrated (client-rendered sites).
    # None skips the wait; a timeout is tolerated because server-rendered HTML may
    # already hold the rows even when the selector never appears.
    ready_selector: str | None = None
    settle_ms: int = 2_500
    ready_timeout_ms: int = 20_000
    # "pdf": every item is a PDF download; "html": render the detail page (with a
    # PDF fallback when the page text is thin, e.g. PFRDA detail pages that are
    # just a wrapper around the circular PDF).
    fetch_kind: str = "html"
    content_selectors: tuple[str, ...] = ("article", "main", ".content", ".portlet-body")
    min_detail_chars: int = 500

    # --- browser boilerplate -------------------------------------------------
    @contextlib.asynccontextmanager
    async def _page(self) -> AsyncIterator[Page]:
        """Same lifecycle as BaseScraper._page but with a realistic desktop
        profile; the honest bot UA gets 403'd by the WAFs these sites sit behind."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=BROWSER_UA,
                viewport=VIEWPORT,
                locale="en-IN",
                ignore_https_errors=True,  # several .gov.in chains are broken
            )
            page = await context.new_page()
            try:
                yield page
            finally:
                await context.close()
                await browser.close()

    # --- discovery ------------------------------------------------------------
    async def render_listing(self, page: Page) -> str:
        """Navigate to the listing and return its rendered HTML (or, for API-backed
        sites, the JSON the page is entitled to fetch). Default: load, wait for
        hydration, snapshot."""
        await page.goto(self.base_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        await self._settle(page)
        return await page.content()

    async def _settle(self, page: Page) -> None:
        if self.ready_selector is not None:
            try:
                await page.wait_for_selector(self.ready_selector, timeout=self.ready_timeout_ms)
            except Exception:  # noqa: BLE001 - rows may be server-rendered already
                log.info(
                    "%s: ready selector %r never appeared", self.scraper_kind, self.ready_selector
                )
        await page.wait_for_timeout(self.settle_ms)

    @abc.abstractmethod
    def parse_listing(self, body: str) -> list[DocMeta]:
        """Extract item rows (title/url/date/id) from the rendered listing body.
        Pure function so it is unit-testable against saved fixtures."""

    async def discover(self, page: Page) -> list[DocMeta]:
        body = await self.render_listing(page)
        metas = self.parse_listing(body)
        seen: set[str] = set()
        unique = [m for m in metas if not (m.source_id in seen or seen.add(m.source_id))]
        return unique[:MAX_ITEMS]

    # --- full-text fetch --------------------------------------------------------
    async def fetch(self, page: Page, meta: DocMeta) -> str:
        if self.fetch_kind == "pdf":
            text = await self._pdf_text(page.context, meta.source_url)
        else:
            text = await self._html_text(page, meta)
        return text[:MAX_TEXT_CHARS]

    async def _pdf_text(self, context: BrowserContext, url: str) -> str:
        """Download bytes through the browser context (its cookies carry any
        WAF tokens) and extract the text layer."""
        resp = await context.request.get(url, timeout=NAV_TIMEOUT_MS)
        if not resp.ok:
            raise RuntimeError(f"download failed with HTTP {resp.status} for {url}")
        return pdf_bytes_to_text(await resp.body())

    async def _pdf_text_in_page(self, page: Page, url: str) -> str:
        """Download a PDF with an in-page ``fetch`` and extract its text. For WAFs
        (NPCI's Akamai) that fingerprint more than cookies and 403 any request not
        issued by the rendered page itself. The page must already be on the site."""
        import base64

        b64 = await page.evaluate(
            """async url => {
                const r = await fetch(url);
                if (!r.ok) throw new Error('HTTP ' + r.status);
                const bytes = new Uint8Array(await r.arrayBuffer());
                let s = '';
                for (let i = 0; i < bytes.length; i += 0x8000)
                    s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
                return btoa(s);
            }""",
            url,
        )
        return pdf_bytes_to_text(base64.b64decode(b64))

    async def _html_text(self, page: Page, meta: DocMeta) -> str:
        await page.goto(meta.source_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        await page.wait_for_timeout(self.settle_ms)
        text = ""
        for sel in self.content_selectors:
            el = await page.query_selector(sel)
            if el:
                text = (await el.inner_text()).strip()
                if text:
                    break
        if not text:
            text = (await page.inner_text("body")).strip()
        # Thin wrapper page around an attached PDF -> pull the PDF instead.
        if len(text) < self.min_detail_chars:
            pdf = await page.query_selector("a[href*='.pdf' i]")
            href = (await pdf.get_attribute("href")) if pdf else None
            if href:
                from urllib.parse import urljoin

                try:
                    pdf_text = await self._pdf_text(page.context, urljoin(page.url, href))
                    if len(pdf_text) > len(text):
                        return pdf_text
                except Exception as exc:  # noqa: BLE001 - keep the page text instead
                    log.warning("%s: pdf fallback failed for %s: %s", self.scraper_kind, href, exc)
        return text
