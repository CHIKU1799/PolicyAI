"""Concrete RSS/Atom feed sources, built on ``FeedScraper``.

These broaden coverage beyond RBI/SEBI/IRDAI to tax, trade, cyber and gazette
notifications, and give a browser-free path that's lighter than Playwright. Each
class only declares its ``scraper_kind`` + ``regulator_key``; the feed URL is
configured per ``MonitoringSource`` (so a URL can be re-tuned without code changes).
eGazette also serves as the MCA bypass: MCA notifications are published there in
authoritative form, away from MCA's Akamai bot wall.

Source status audit (2026-07-29): PIB and RBI press feeds work over plain HTTP.
The rest are disabled in ``monitoring_sources`` because their endpoints are
bot-walled or gone for non-browser clients: CERT-In/FIU serve a JS challenge
page instead of XML, NPCI/CBDT return WAF 403s, PFRDA/IFSCA have no /rss at
all, DGFT emits junk past the document root, eGazette's TLS chain is broken.
Re-enabling them needs Playwright-rendered fetching (see the RBI/SEBI scrapers)
or discovered alternate endpoints; flip ``enabled`` in the DB once fixed.
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


class CERTInFeed(FeedScraper):
    """CERT-In — cyber-security directions and advisories (IT Act / data security)."""

    scraper_kind = "certin_rss"
    regulator_key = "certin"


class CBICFeed(FeedScraper):
    """CBIC — indirect tax / GST / customs circulars and notifications."""

    scraper_kind = "cbic_rss"
    regulator_key = "cbic"


class CBDTFeed(FeedScraper):
    """CBDT — direct-tax circulars and notifications."""

    scraper_kind = "cbdt_rss"
    regulator_key = "cbdt"


class DGFTFeed(FeedScraper):
    """DGFT — foreign-trade policy notifications and public notices."""

    scraper_kind = "dgft_rss"
    regulator_key = "dgft"


class EGazetteFeed(FeedScraper):
    """eGazette — authoritative acts/rules; also the MCA-notifications bypass."""

    scraper_kind = "egazette_rss"
    regulator_key = "egazette"


class PFRDAFeed(FeedScraper):
    """PFRDA — pension-sector circulars (NPS/APY intermediaries, pension funds)."""

    scraper_kind = "pfrda_rss"
    regulator_key = "pfrda"


class IFSCAFeed(FeedScraper):
    """IFSCA — unified GIFT-City/IFSC regulator (banking, capital markets, insurance, funds)."""

    scraper_kind = "ifsca_rss"
    regulator_key = "ifsca"


class NPCIFeed(FeedScraper):
    """NPCI — retail-payments circulars/OCs (UPI, IMPS, NACH, RuPay)."""

    scraper_kind = "npci_rss"
    regulator_key = "npci"


class FIUFeed(FeedScraper):
    """FIU-IND — PMLA / AML-CFT directions for reporting entities."""

    scraper_kind = "fiu_rss"
    regulator_key = "fiu_ind"
