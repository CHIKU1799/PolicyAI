"""Scrapers for Indian regulators — RBI, SEBI, IRDAI, MCA (HTML via Playwright)
plus lighter RSS/Atom feed sources (tax, trade, cyber, gazette) via httpx.

``SCRAPER_REGISTRY`` maps a ``MonitoringSource.scraper_kind`` to its scraper class
so the runner can dispatch by configuration rather than hard-coding sources.
"""

from policyai_scrapers.base import BaseScraper, DocMeta
from policyai_scrapers.feed_base import FeedScraper
from policyai_scrapers.feeds import (
    CBDTFeed,
    CBICFeed,
    CERTInFeed,
    DGFTFeed,
    EGazetteFeed,
    FIUFeed,
    IFSCAFeed,
    NPCIFeed,
    PFRDAFeed,
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
    CERTInFeed.scraper_kind: CERTInFeed,
    CBICFeed.scraper_kind: CBICFeed,
    CBDTFeed.scraper_kind: CBDTFeed,
    DGFTFeed.scraper_kind: DGFTFeed,
    EGazetteFeed.scraper_kind: EGazetteFeed,
    # Newly added BFSI regulators (pension, IFSC, payments, financial-intelligence).
    PFRDAFeed.scraper_kind: PFRDAFeed,
    IFSCAFeed.scraper_kind: IFSCAFeed,
    NPCIFeed.scraper_kind: NPCIFeed,
    FIUFeed.scraper_kind: FIUFeed,
}

__all__ = [
    "BaseScraper",
    "DocMeta",
    "FeedScraper",
    "RBIScraper",
    "SEBIScraper",
    "IRDAIScraper",
    "MCAScraper",
    "RBIPressFeed",
    "PIBFeed",
    "CERTInFeed",
    "CBICFeed",
    "CBDTFeed",
    "DGFTFeed",
    "EGazetteFeed",
    "PFRDAFeed",
    "IFSCAFeed",
    "NPCIFeed",
    "FIUFeed",
    "SCRAPER_REGISTRY",
]
