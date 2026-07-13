"""HTTP/RSS feed scraper — a lightweight, browser-free sibling of ``BaseScraper``.

Many regulators publish an RSS/Atom feed of their notifications. Pulling those over
``httpx`` is far faster and far more robust than driving Playwright over brittle HTML,
and the feed already gives us clean titles, links and publish dates. A concrete feed
source just subclasses this and sets ``scraper_kind`` + ``regulator_key``; the feed URL
comes from ``MonitoringSource.base_url`` (passed to the constructor by the runner), so
the same code serves every feed.

Parsing is namespace-agnostic (matches on local tag names) so it handles both RSS
``<item>`` and Atom ``<entry>``. When a feed entry carries little inline text, the full
article page is fetched and stripped to text as a fallback.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx

from policyai_scrapers.base import FETCH_ATTEMPTS, REQUEST_DELAY, BaseScraper, DocMeta
from policyai_scrapers.util import log, select_new, with_retry

# Several gov gateways (PIB, NIC WAFs) 403 anything with "bot" in the UA even on
# their public RSS endpoints, so present as a plain feed-reader browser instead.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TIMEOUT = httpx.Timeout(30.0)
_ENTITIES = (
    ("&amp;", "&"),
    ("&lt;", "<"),
    ("&gt;", ">"),
    ("&quot;", '"'),
    ("&#39;", "'"),
    ("&nbsp;", " "),
)


def strip_html(html: str) -> str:
    """Crude HTML -> text: drop tags, unescape common entities, collapse whitespace."""
    text = _TAG_RE.sub(" ", html or "")
    for a, b in _ENTITIES:
        text = text.replace(a, b)
    return _WS_RE.sub(" ", text).strip()


def parse_feed_date(value: str | None) -> date | None:
    """Parse an RSS (RFC-822) or Atom (ISO-8601) date, best-effort."""
    if not value:
        return None
    value = value.strip()
    try:
        return parsedate_to_datetime(value).date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%b %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value[:20], fmt).date()
        except ValueError:
            continue
    return None


def parse_feed(xml_text: str) -> list[dict]:
    """Return a list of {title, link, id, date, content} dicts for each feed entry,
    handling RSS ``<item>`` and Atom ``<entry>`` without caring about namespaces."""

    def ln(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].lower()

    root = ET.fromstring(xml_text)
    items: list[dict] = []
    for el in root.iter():
        if ln(el.tag) not in ("item", "entry"):
            continue
        f: dict = {"title": None, "link": None, "id": None, "date": None, "content": ""}
        for c in el:
            name = ln(c.tag)
            if name == "title" and f["title"] is None:
                f["title"] = (c.text or "").strip()
            elif name == "link":
                href = c.get("href")  # Atom: <link href="...">
                if href:
                    f["link"] = href
                elif (c.text or "").strip():  # RSS: <link>...</link>
                    f["link"] = c.text.strip()
            elif name in ("guid", "id") and f["id"] is None:
                f["id"] = (c.text or "").strip()
            elif name in ("pubdate", "published", "updated", "date") and f["date"] is None:
                f["date"] = (c.text or "").strip()
            elif name in ("encoded", "content", "description", "summary"):
                val = c.text or ""
                if len(val) > len(f["content"]):  # keep the richest body
                    f["content"] = val
        items.append(f)
    return items


class FeedScraper(BaseScraper):
    """RSS/Atom feed source. Subclasses set ``scraper_kind`` + ``regulator_key``."""

    item_limit: int = 40
    min_chars: int = 400  # below this, fetch the article page for fuller text
    max_chars: int = 40000
    # When set, keep only entries whose title contains one of these substrings
    # (case-insensitive). Press-release feeds mix regulatory actions with daily
    # operational noise; the filter keeps extraction spend on the former.
    title_include: tuple[str, ...] = ()

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=_TIMEOUT, headers={"User-Agent": _UA}, follow_redirects=True
        )

    async def _discover(self, client: httpx.AsyncClient) -> list[DocMeta]:
        resp = await client.get(self.base_url)
        resp.raise_for_status()
        metas: list[DocMeta] = []
        for f in parse_feed(resp.text)[: self.item_limit]:
            link = f["link"] or f["id"]
            if not link or not f["title"]:
                continue
            if self.title_include and not any(
                k.lower() in f["title"].lower() for k in self.title_include
            ):
                continue
            metas.append(
                DocMeta(
                    source=self.regulator_key,
                    source_id=(f["id"] or link)[:256],
                    source_url=link,
                    title=f["title"],
                    published_date=parse_feed_date(f["date"]),
                    raw_text=strip_html(f["content"]),
                )
            )
        return metas

    async def _fetch_text(self, client: httpx.AsyncClient, meta: DocMeta) -> str:
        resp = await client.get(meta.source_url)
        resp.raise_for_status()
        return strip_html(resp.text)

    # --- BaseScraper interface (page is unused; feeds don't need a browser) ---
    async def discover(self, page=None) -> list[DocMeta]:  # type: ignore[override]
        async with self._new_client() as client:
            return await self._discover(client)

    async def fetch(self, page, meta: DocMeta) -> str:  # type: ignore[override]
        async with self._new_client() as client:
            return await self._fetch_text(client, meta)

    async def collect(self, known_ids: set[str] | None = None) -> list[DocMeta]:
        """Fetch the feed once, drop already-ingested entries (the watermark), then
        backfill body text from the article page only for entries whose inline
        content is thin. Article fetches retry on transient errors; per-item
        failures keep the feed snippet rather than dropping the item."""
        out: list[DocMeta] = []
        async with self._new_client() as client:
            try:
                discovered = await with_retry(
                    lambda: self._discover(client),
                    attempts=FETCH_ATTEMPTS,
                    label=f"{self.scraper_kind}:feed",
                )
            except Exception as exc:  # noqa: BLE001 - a bad feed shouldn't crash the run
                log.warning(
                    "%s: feed fetch failed for %s: %s", self.scraper_kind, self.base_url, exc
                )
                return out
            self.discovered_count = len(discovered)
            metas = select_new(discovered, known_ids)
            log.info("%s: discovered %d, %d new", self.scraper_kind, len(discovered), len(metas))
            for meta in metas:
                if len(meta.raw_text) < self.min_chars:
                    try:
                        await asyncio.sleep(REQUEST_DELAY)
                        meta.raw_text = await with_retry(
                            lambda m=meta: self._fetch_text(client, m),
                            attempts=FETCH_ATTEMPTS,
                            label=f"{self.scraper_kind}:{meta.source_id}",
                        )
                    except Exception as exc:  # noqa: BLE001 - keep the feed snippet instead
                        log.warning(
                            "%s: page fetch failed for %s: %s",
                            self.scraper_kind,
                            meta.source_url,
                            exc,
                        )
                meta.raw_text = (meta.raw_text or "")[: self.max_chars]
                if meta.raw_text.strip():
                    out.append(meta)
        return out
