"""Scrapers for Indian regulators: RBI, SEBI, IRDAI, MCA (HTML via Playwright),
lighter RSS/Atom feed sources via httpx, and browser-rendered listing sources
(CERT-In, NPCI, PFRDA, IFSCA, FIU-IND, DGFT) for sites that bot-wall plain HTTP.

``SCRAPER_REGISTRY`` maps a ``MonitoringSource.scraper_kind`` to its scraper class
so the runner can dispatch by configuration rather than hard-coding sources.
"""

from policyai_scrapers.base import BaseScraper, DocMeta
from policyai_scrapers.browser_base import BrowserListScraper
from policyai_scrapers.browser_sources import (
    CERTInAdvisoriesScraper,
    DGFTNotificationsScraper,
    FIUComplianceOrdersScraper,
    IFSCACircularsScraper,
    NPCICircularsScraper,
    PFRDACircularsScraper,
)
from policyai_scrapers.feed_base import FeedScraper
from policyai_scrapers.feeds import (
    CBDTFeed,
    CBICFeed,
    EGazetteFeed,
    PIBFeed,
    RBIPressFeed,
)
from policyai_scrapers.irdai import IRDAIScraper
from policyai_scrapers.mca import MCAScraper
from policyai_scrapers.rbi import RBIScraper
from policyai_scrapers.sebi import SEBIScraper

__version__ = "0.2.0"

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    RBIScraper.scraper_kind: RBIScraper,
    SEBIScraper.scraper_kind: SEBIScraper,  # sebi_circulars (master circulars)
    "sebi_general_circulars": SEBIScraper,  # SEBI general circulars listing
    IRDAIScraper.scraper_kind: IRDAIScraper,
    MCAScraper.scraper_kind: MCAScraper,
    # Lightweight RSS/Atom feed sources (no browser).
    RBIPressFeed.scraper_kind: RBIPressFeed,
    PIBFeed.scraper_kind: PIBFeed,
    CBICFeed.scraper_kind: CBICFeed,
    CBDTFeed.scraper_kind: CBDTFeed,
    EGazetteFeed.scraper_kind: EGazetteFeed,
    # Browser-rendered listing sources. These keep the *_rss kinds of the feed
    # scrapers they replaced, so the existing monitoring_sources rows re-enable
    # straight onto the new implementation (see browser_sources.py).
    CERTInAdvisoriesScraper.scraper_kind: CERTInAdvisoriesScraper,
    NPCICircularsScraper.scraper_kind: NPCICircularsScraper,
    PFRDACircularsScraper.scraper_kind: PFRDACircularsScraper,
    IFSCACircularsScraper.scraper_kind: IFSCACircularsScraper,
    FIUComplianceOrdersScraper.scraper_kind: FIUComplianceOrdersScraper,
    DGFTNotificationsScraper.scraper_kind: DGFTNotificationsScraper,
}

__all__ = [
    "BaseScraper",
    "BrowserListScraper",
    "DocMeta",
    "FeedScraper",
    "RBIScraper",
    "SEBIScraper",
    "IRDAIScraper",
    "MCAScraper",
    "RBIPressFeed",
    "PIBFeed",
    "CBICFeed",
    "CBDTFeed",
    "EGazetteFeed",
    "CERTInAdvisoriesScraper",
    "NPCICircularsScraper",
    "PFRDACircularsScraper",
    "IFSCACircularsScraper",
    "FIUComplianceOrdersScraper",
    "DGFTNotificationsScraper",
    "SCRAPER_REGISTRY",
]
