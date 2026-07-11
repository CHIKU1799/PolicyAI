"""Unit tests for the scrapers package — pure logic, no browser/DB/network."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from policyai_graph.models_app import MonitoringSource
from policyai_graph.seed import MONITORING_SOURCES
from policyai_scrapers import SCRAPER_REGISTRY
from policyai_scrapers.base import DocMeta
from policyai_scrapers.feed_base import parse_feed, parse_feed_date, strip_html
from policyai_scrapers.rbi import RBIScraper, _first_date, _is_empty_notice, _looks_like_title
from policyai_scrapers.runner import _is_due
from policyai_scrapers.util import select_new, with_retry

RBI_URL = "https://www.rbi.org.in/Scripts/NotificationUser.aspx"


def test_registry_covers_all_seeded_sources():
    """Every seeded monitoring source must have a scraper, and vice versa."""
    seeded_kinds = {s["scraper_kind"] for s in MONITORING_SOURCES}
    assert seeded_kinds == set(SCRAPER_REGISTRY)
    # and each scraper's regulator_key matches its seed entry
    by_kind = {s["scraper_kind"]: s["regulator_key"] for s in MONITORING_SOURCES}
    for kind, cls in SCRAPER_REGISTRY.items():
        assert cls.regulator_key == by_kind[kind]


def test_content_hash_is_stable_and_change_sensitive():
    a = DocMeta(source="rbi", source_id="1", source_url="u", title="T", raw_text="body")
    b = DocMeta(source="rbi", source_id="1", source_url="u", title="T", raw_text="body")
    assert a.content_hash() == b.content_hash()  # same content -> same hash (dedup)

    c = DocMeta(source="rbi", source_id="1", source_url="u", title="T", raw_text="EDITED")
    assert a.content_hash() != c.content_hash()  # edited body -> re-ingest

    d = DocMeta(source="rbi", source_id="1", source_url="u", title="NEW", raw_text="body")
    assert a.content_hash() != d.content_hash()  # edited title -> re-ingest


def test_parse_feed_handles_rss_and_atom():
    rss = """<?xml version='1.0'?>
    <rss version='2.0' xmlns:content='http://purl.org/rss/1.0/modules/content/'>
      <channel>
        <item>
          <title>Master Direction on Pricing of Credit</title>
          <link>https://example.gov.in/circular/2026-001</link>
          <guid>CIRC-2026-001</guid>
          <pubDate>Mon, 22 Jun 2026 10:00:00 +0530</pubDate>
          <description>Short blurb.</description>
          <content:encoded>The fuller body text of the circular goes here.</content:encoded>
        </item>
      </channel>
    </rss>"""
    items = parse_feed(rss)
    assert len(items) == 1
    it = items[0]
    assert it["title"] == "Master Direction on Pricing of Credit"
    assert it["link"] == "https://example.gov.in/circular/2026-001"
    assert it["id"] == "CIRC-2026-001"
    # content:encoded is richer than description -> it wins
    assert "fuller body text" in it["content"]
    assert parse_feed_date(it["date"]) == date(2026, 6, 22)

    atom = """<?xml version='1.0'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry>
        <title>Advisory 2026-07</title>
        <link href='https://cert.example.in/adv/2026-07'/>
        <id>adv-2026-07</id>
        <updated>2026-07-01T09:30:00Z</updated>
        <summary>Patch your systems.</summary>
      </entry>
    </feed>"""
    items = parse_feed(atom)
    assert len(items) == 1
    assert items[0]["link"] == "https://cert.example.in/adv/2026-07"
    assert parse_feed_date(items[0]["date"]) == date(2026, 7, 1)


def test_strip_html_unescapes_and_collapses():
    assert strip_html("<p>Hello&nbsp;&amp; <b>world</b></p>") == "Hello & world"


def test_select_new_applies_watermark():
    metas = [
        DocMeta(source="rbi", source_id="1", source_url="u1", title="A"),
        DocMeta(source="rbi", source_id="2", source_url="u2", title="B"),
        DocMeta(source="rbi", source_id="3", source_url="u3", title="C"),
    ]
    # Known ids 1 and 2 are skipped; only the new doc 3 survives.
    fresh = select_new(metas, {"1", "2"})
    assert [m.source_id for m in fresh] == ["3"]
    # No watermark (first crawl) -> everything is new.
    assert len(select_new(metas, None)) == 3
    assert len(select_new(metas, set())) == 3


@pytest.mark.asyncio
async def test_with_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return "ok"

    out = await with_retry(flaky, attempts=3, base_delay=0.0, label="t")
    assert out == "ok" and calls["n"] == 3


@pytest.mark.asyncio
async def test_with_retry_reraises_after_exhausting_attempts():
    async def always_fails():
        raise TimeoutError("nope")

    with pytest.raises(TimeoutError):
        await with_retry(always_fails, attempts=2, base_delay=0.0, label="t")


@pytest.mark.asyncio
async def test_rbi_deep_enumerates_id_range_without_network():
    """Deep RBI discovery with an explicit range enumerates ids and never touches the
    page (page is only used to read the listing max when to_id is omitted)."""
    scraper = RBIScraper(RBI_URL, deep=True, from_id=12670, to_id=12673)
    metas = await scraper.discover(page=None)  # page unused when to_id is set
    assert [m.source_id for m in metas] == ["12670", "12671", "12672", "12673"]
    assert all(m.source == "rbi" and m.title == "" for m in metas)
    assert metas[1].source_url == f"{RBI_URL}?Id=12671&Mode=0"


@pytest.mark.asyncio
async def test_rbi_deep_range_is_order_insensitive():
    scraper = RBIScraper(RBI_URL, deep=True, from_id=13, to_id=10)
    metas = await scraper.discover(page=None)
    assert [m.source_id for m in metas] == ["10", "11", "12", "13"]


def test_rbi_empty_notice_detection():
    assert _is_empty_notice("") is True
    assert _is_empty_notice("   No record found   ") is True
    real = (
        "The Reserve Bank of India has come across instances of unauthorised entities "
        "offering foreign exchange trading facilities to Indian residents. " * 6
    )
    assert _is_empty_notice(real) is False


def test_looks_like_title_rejects_junk():
    # Real titles pass.
    assert _looks_like_title("Unauthorised foreign exchange transactions")
    assert _looks_like_title("Master Direction on Pricing of Credit")
    # File-size labels, format tags, bare dates, too-short/no-alpha -> rejected.
    assert not _looks_like_title("(336 kb)")
    assert not _looks_like_title("1.2 MB")
    assert not _looks_like_title("PDF")
    assert not _looks_like_title("April 24, 2024")
    assert not _looks_like_title("short")
    assert not _looks_like_title("1234567890123")


def test_first_date_parses_notification_dateline():
    assert _first_date("RBI/2024-25/25 ... dated April 24, 2024 ...") == date(2024, 4, 24)
    assert _first_date("Issued on 15-06-2026 to all banks") == date(2026, 6, 15)
    assert _first_date("no date anywhere here") is None


def test_is_due_cadence_logic():
    now = datetime.now(UTC)

    never = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    never.enabled = True
    never.cadence_hours = 6
    never.last_scanned_at = None
    assert _is_due(never, now) is True  # never scanned -> due

    fresh = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    fresh.enabled = True
    fresh.cadence_hours = 6
    fresh.last_scanned_at = now - timedelta(hours=1)
    assert _is_due(fresh, now) is False  # within cadence -> not due

    stale = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    stale.enabled = True
    stale.cadence_hours = 6
    stale.last_scanned_at = now - timedelta(hours=7)
    assert _is_due(stale, now) is True  # past cadence -> due

    disabled = MonitoringSource(scraper_kind="x", regulator_key="x", name="x", base_url="u")
    disabled.enabled = False
    disabled.cadence_hours = 6
    disabled.last_scanned_at = None
    assert _is_due(disabled, now) is False  # disabled -> never due
