"""Unit tests for the browser-source listing parse hooks.

``parse_listing`` is pure Python by design, so these run against small fixtures
trimmed from the real listing pages (captured 2026-07) with no browser/network.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from policyai_scrapers.browser_base import parse_listing_date
from policyai_scrapers.browser_sources import (
    CERTInAdvisoriesScraper,
    DGFTNotificationsScraper,
    FIUComplianceOrdersScraper,
    IFSCACircularsScraper,
    NPCICircularsScraper,
    PFRDACircularsScraper,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_parse_listing_date_formats():
    assert parse_listing_date("21/07/2026") == date(2026, 7, 21)  # IFSCA, DGFT
    assert parse_listing_date("14-07-2026") == date(2026, 7, 14)  # PFRDA
    assert parse_listing_date("July   22, 2026") == date(2026, 7, 22)  # CERT-In
    assert parse_listing_date("December 30th 2025") == date(2025, 12, 30)  # FIU-IND
    assert parse_listing_date("(July 22, 2026)") == date(2026, 7, 22)
    assert parse_listing_date("not a date") is None
    assert parse_listing_date(None) is None


def test_certin_parse_listing():
    scraper = CERTInAdvisoriesScraper("https://www.cert-in.org.in/s2cMainServlet?pageid=PUBADVLIST")
    metas = scraper.parse_listing(_read("certin_advisories.html"))
    assert len(metas) == 3
    first = metas[0]
    assert first.source == "certin"
    assert first.source_id == "CIAD-2026-0036"
    assert first.title == (
        "CERT-In Advisory CIAD-2026-0036: Multiple Vulnerabilities in Oracle Products"
    )
    assert first.source_url == (
        "https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES02&VLCODE=CIAD-2026-0036"
    )
    assert first.published_date == date(2026, 7, 22)
    # every item resolves title + absolute url + id
    assert all(m.title and m.source_url.startswith("https://") and m.source_id for m in metas)


def test_npci_parse_listing():
    scraper = NPCICircularsScraper("https://www.npci.org.in/circulars/upi")
    metas = scraper.parse_listing(_read("npci_circulars.json"))
    # 5 files in the fixture; the first has media: null and must be skipped
    assert len(metas) == 4
    first = metas[0]
    assert first.source == "npci"
    assert first.source_id == "3953"
    assert first.title.startswith("UPI | OC 235 | FY 26-27")
    assert first.source_url.startswith("https://www.npci.org.in/uploads/")
    assert first.source_url.endswith(".pdf")


def test_npci_parse_listing_tolerates_junk():
    scraper = NPCICircularsScraper("https://www.npci.org.in/circulars/upi")
    assert scraper.parse_listing("") == []
    assert scraper.parse_listing("<html>WAF challenge</html>") == []


def test_pfrda_parse_listing():
    scraper = PFRDACircularsScraper(
        "https://www.pfrda.org.in/regulatory-framework/circulars/active-circulars"
    )
    metas = scraper.parse_listing(_read("pfrda_circulars.html"))
    assert len(metas) == 3
    first = metas[0]
    assert first.source == "pfrda"
    assert first.title.startswith("Circular - Introduction of NPS PRIDE")
    assert first.published_date == date(2026, 7, 14)
    assert first.source_url.startswith("https://www.pfrda.org.in/w/")
    assert "?" not in first.source_url  # back-url tracking params dropped
    assert first.source_id  # slug


def test_ifsca_parse_listing():
    scraper = IFSCACircularsScraper("https://ifsca.gov.in/Legal/Index/wF6kttc1JR8=")
    metas = scraper.parse_listing(_read("ifsca_circulars.html"))
    assert len(metas) == 5
    first = metas[0]
    assert first.source == "ifsca"
    assert first.title == (
        "Framework on capital relief and prudential requirements for factoring transactions"
    )
    assert first.published_date == date(2026, 7, 21)
    # GetFileView (HTML viewer) is rewritten to ViewFile (raw PDF)
    assert "/CommonDirect/ViewFile?" in first.source_url
    assert first.source_id == "29709e474fe6b066fc0cb19f7d790767"


def test_fiu_parse_listing():
    scraper = FIUComplianceOrdersScraper(
        "https://fiuindia.gov.in/files/Compliance_Orders/orders.html"
    )
    metas = scraper.parse_listing(_read("fiu_orders.html"))
    assert len(metas) == 6
    first = metas[0]
    assert first.source == "fiu_ind"
    assert "Gandhinagar Nagarik Cooperative Bank" in first.title
    assert first.published_date == date(2025, 12, 30)
    # relative ../../pdfs link resolved against the listing url
    assert first.source_url == "https://fiuindia.gov.in/pdfs/judgements/TGNCBL_Order_3_2025.pdf"
    assert first.source_id == "TGNCBL_Order_3_2025.pdf"


def test_dgft_parse_listing():
    scraper = DGFTNotificationsScraper("https://www.dgft.gov.in/CP/?opt=notification")
    metas = scraper.parse_listing(_read("dgft_notifications.html"))
    assert len(metas) == 5
    first = metas[0]
    assert first.source == "dgft"
    assert first.title.startswith("Notification No. 26/2026-27: Harmonisation of Schedule-II")
    assert first.published_date == date(2026, 7, 27)
    assert first.source_url.startswith("https://content.dgft.gov.in/")
    assert " " not in first.source_url  # spaces in gov filenames are quoted
    assert first.source_id == "e81c613a-9670-4ab5-9522-9faac4cd9da4"


def test_dedupe_and_cap_in_discover_shape():
    """parse hooks may repeat ids (some listings render rows twice); discover()
    dedupes on source_id, so hooks only need to be order-preserving."""
    scraper = IFSCACircularsScraper("https://ifsca.gov.in/Legal/Index/wF6kttc1JR8=")
    body = _read("ifsca_circulars.html")
    metas = scraper.parse_listing(body + body)  # duplicated listing
    ids = [m.source_id for m in metas]
    assert len(ids) == 10  # parse keeps duplicates...
    deduped = list(dict.fromkeys(ids))
    assert len(deduped) == 5  # ...discover()'s seen-set collapses them
