"""Scrapers for RBI, SEBI, IRDAI, and MCA regulatory documents.

``SCRAPER_REGISTRY`` maps a ``MonitoringSource.scraper_kind`` to its scraper class
so the runner can dispatch by configuration rather than hard-coding sources.
"""

from policyai_scrapers.base import BaseScraper, DocMeta
from policyai_scrapers.irdai import IRDAIScraper
from policyai_scrapers.mca import MCAScraper
from policyai_scrapers.rbi import RBIScraper
from policyai_scrapers.sebi import SEBIScraper

__version__ = "0.1.0"

SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    RBIScraper.scraper_kind: RBIScraper,
    SEBIScraper.scraper_kind: SEBIScraper,  # sebi_circulars (master circulars)
    "sebi_general_circulars": SEBIScraper,  # SEBI general circulars listing
    IRDAIScraper.scraper_kind: IRDAIScraper,
    MCAScraper.scraper_kind: MCAScraper,
}

__all__ = [
    "BaseScraper",
    "DocMeta",
    "RBIScraper",
    "SEBIScraper",
    "IRDAIScraper",
    "MCAScraper",
    "SCRAPER_REGISTRY",
]
