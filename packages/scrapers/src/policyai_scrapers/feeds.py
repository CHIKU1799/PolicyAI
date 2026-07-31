"""Concrete RSS/Atom feed sources, built on ``FeedScraper``.

These broaden coverage beyond RBI/SEBI/IRDAI to tax, trade, cyber and gazette
notifications, and give a browser-free path that's lighter than Playwright. Each
class only declares its ``scraper_kind`` + ``regulator_key``; the feed URL is
configured per ``MonitoringSource`` (so a URL can be re-tuned without code changes).
eGazette also serves as the MCA bypass: MCA notifications are published there in
authoritative form, away from MCA's Akamai bot wall.

Source status audit (2026-07-31): PIB and RBI press feeds work over plain HTTP
and stay on this module. CERT-In, NPCI, PFRDA, IFSCA, FIU-IND and DGFT could not
be reached over plain HTTP (JS challenges, WAF 403s, no /rss, junk XML); they
now run as Playwright browser-rendered listing scrapers in ``browser_sources.py``
under the same ``scraper_kind`` names. CERT-In, PFRDA, IFSCA and FIU-IND are
enabled in ``monitoring_sources`` with live-verified listing URLs and full-text
fetch. NPCI and DGFT are wired and discovery-verified but stay disabled: both
publish scanned image PDFs with no text layer, so full text needs OCR (their
rows already carry the working listing URLs, flip ``enabled`` once OCR exists).
Still dead and disabled:

* CBDT (incometaxindia.gov.in): Akamai returns 403 even to a real headless
  Chromium with a desktop profile; needs a non-headless or residential path.
* CBIC (taxinformation.cbic.gov.in): the Angular portal takes ~80s to boot in
  headless Chromium and then renders an in-app error on the circulars route;
  www.cbic.gov.in itself exposes no circular listing outside that portal.
* eGazette (egazette.gov.in): broken TLS chain plus a session-keyed ASP.NET
  search flow with no stable listing page; not worth automating.
"""

from __future__ import annotations

from policyai_scrapers.feed_base import FeedScraper


class RBIPressFeed(FeedScraper):
    """RBI press releases RSS. The feed mixes daily operational noise (money
    market ops, auction results) with real regulatory actions; the title filter
    keeps only the latter so extraction spend goes to documents that matter."""

    scraper_kind = "rbi_press_rss"
    regulator_key = "rbi"
    title_include = (
        "direction",
        "circular",
        "guideline",
        "regulation",
        "penalty",
        "monetary policy",
        "framework",
        "master",
        "notification",
        "amendment",
        "kyc",
        "licence",
        "license",
        "authorisation",
        "cancel",
    )


class PIBFeed(FeedScraper):
    """Press Information Bureau — cross-ministry policy announcements (incl. MCA)."""

    scraper_kind = "pib_rss"
    regulator_key = "pib"


class CBICFeed(FeedScraper):
    """CBIC — indirect tax / GST / customs circulars and notifications."""

    scraper_kind = "cbic_rss"
    regulator_key = "cbic"


class CBDTFeed(FeedScraper):
    """CBDT — direct-tax circulars and notifications."""

    scraper_kind = "cbdt_rss"
    regulator_key = "cbdt"


class EGazetteFeed(FeedScraper):
    """eGazette — authoritative acts/rules; also the MCA-notifications bypass."""

    scraper_kind = "egazette_rss"
    regulator_key = "egazette"
