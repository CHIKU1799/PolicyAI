"""Seed canonical graph data: regulators + sub-departments, entity classes, parent acts.

Idempotent: re-running will not duplicate rows. Uses the `canonical_key` property
on each node as the deduplication identity.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.graph_ops import get_or_create_edge as _get_or_create_edge
from policyai_graph.graph_ops import get_or_create_node as _get_or_create_node
from policyai_graph.models import EdgeType, Node, NodeType
from policyai_graph.models_app import MonitoringSource

REGULATORS: list[dict] = [
    {
        "canonical_key": "rbi",
        "name": "Reserve Bank of India",
        "short_name": "RBI",
        "kind": "central_bank",
        "departments": [
            {"canonical_key": "rbi.dor", "name": "Department of Regulation", "short_name": "DoR"},
            {"canonical_key": "rbi.dos", "name": "Department of Supervision", "short_name": "DoS"},
            {
                "canonical_key": "rbi.dpss",
                "name": "Department of Payment and Settlement Systems",
                "short_name": "DPSS",
            },
            {
                "canonical_key": "rbi.fed",
                "name": "Foreign Exchange Department",
                "short_name": "FED",
            },
            {
                "canonical_key": "rbi.fmrd",
                "name": "Financial Markets Regulation Department",
                "short_name": "FMRD",
            },
            {
                "canonical_key": "rbi.cepd",
                "name": "Consumer Education and Protection Department",
                "short_name": "CEPD",
            },
        ],
    },
    {
        "canonical_key": "sebi",
        "name": "Securities and Exchange Board of India",
        "short_name": "SEBI",
        "kind": "securities_regulator",
        "departments": [
            {
                "canonical_key": "sebi.imd",
                "name": "Investment Management Department",
                "short_name": "IMD",
            },
            {
                "canonical_key": "sebi.mrd",
                "name": "Market Regulation Department",
                "short_name": "MRD",
            },
            {
                "canonical_key": "sebi.cfd",
                "name": "Corporation Finance Department",
                "short_name": "CFD",
            },
            {
                "canonical_key": "sebi.afd",
                "name": "Alternative Investment Fund and Foreign Portfolio Investors Department",
                "short_name": "AFD",
            },
            {
                "canonical_key": "sebi.ddhs",
                "name": "Department of Debt and Hybrid Securities",
                "short_name": "DDHS",
            },
            {
                "canonical_key": "sebi.cdmrd",
                "name": "Commodity Derivatives Market Regulation Department",
                "short_name": "CDMRD",
            },
        ],
    },
    {
        "canonical_key": "irdai",
        "name": "Insurance Regulatory and Development Authority of India",
        "short_name": "IRDAI",
        "kind": "insurance_regulator",
        "departments": [
            {
                "canonical_key": "irdai.life",
                "name": "Life Insurance Department",
                "short_name": "Life",
            },
            {
                "canonical_key": "irdai.nonlife",
                "name": "Non-Life Insurance Department",
                "short_name": "Non-Life",
            },
            {
                "canonical_key": "irdai.health",
                "name": "Health Insurance Department",
                "short_name": "Health",
            },
            {
                "canonical_key": "irdai.dist",
                "name": "Distribution Department",
                "short_name": "Distribution",
            },
            {
                "canonical_key": "irdai.inv",
                "name": "Investment Department",
                "short_name": "Investment",
            },
            {
                "canonical_key": "irdai.actuarial",
                "name": "Actuarial Department",
                "short_name": "Actuarial",
            },
        ],
    },
    {
        "canonical_key": "mca",
        "name": "Ministry of Corporate Affairs",
        "short_name": "MCA",
        "kind": "ministry",
        "departments": [
            {
                "canonical_key": "mca.roc",
                "name": "Registrar of Companies",
                "short_name": "RoC",
            },
            {
                "canonical_key": "mca.iepfa",
                "name": "Investor Education and Protection Fund Authority",
                "short_name": "IEPFA",
            },
            {
                "canonical_key": "mca.nfra",
                "name": "National Financial Reporting Authority",
                "short_name": "NFRA",
            },
        ],
    },
    {
        "canonical_key": "cbdt",
        "name": "Central Board of Direct Taxes",
        "short_name": "CBDT",
        "kind": "tax_authority",
        "departments": [
            {
                "canonical_key": "cbdt.tpl",
                "name": "Tax Policy and Legislation",
                "short_name": "TPL",
            },
        ],
    },
    {
        "canonical_key": "cbic",
        "name": "Central Board of Indirect Taxes and Customs",
        "short_name": "CBIC",
        "kind": "tax_authority",
        "departments": [
            {"canonical_key": "cbic.gst", "name": "GST Policy Wing", "short_name": "GST"},
            {"canonical_key": "cbic.customs", "name": "Customs Wing", "short_name": "Customs"},
        ],
    },
    {
        "canonical_key": "npci",
        "name": "National Payments Corporation of India",
        "short_name": "NPCI",
        "kind": "payment_system_operator",
        "departments": [],
    },
    {
        "canonical_key": "certin",
        "name": "Indian Computer Emergency Response Team",
        "short_name": "CERT-In",
        "kind": "cyber_authority",
        "departments": [],
    },
    {
        "canonical_key": "meity",
        "name": "Ministry of Electronics and Information Technology",
        "short_name": "MeitY",
        "kind": "ministry",
        "departments": [],
    },
    {
        "canonical_key": "dgft",
        "name": "Directorate General of Foreign Trade",
        "short_name": "DGFT",
        "kind": "trade_authority",
        "departments": [],
    },
    {
        "canonical_key": "fiu_ind",
        "name": "Financial Intelligence Unit — India",
        "short_name": "FIU-IND",
        "kind": "financial_intelligence",
        "departments": [],
    },
    {
        "canonical_key": "pfrda",
        "name": "Pension Fund Regulatory and Development Authority",
        "short_name": "PFRDA",
        "kind": "pension_regulator",
        "departments": [],
    },
    {
        "canonical_key": "ifsca",
        "name": "International Financial Services Centres Authority",
        "short_name": "IFSCA",
        "kind": "unified_ifsc_regulator",
        "departments": [],
    },
    {
        "canonical_key": "pib",
        "name": "Press Information Bureau",
        "short_name": "PIB",
        "kind": "government_communications",
        "departments": [],
    },
    {
        "canonical_key": "egazette",
        "name": "The Gazette of India",
        "short_name": "eGazette",
        "kind": "official_gazette",
        "departments": [],
    },
]

ENTITY_CLASSES: list[dict] = [
    {"canonical_key": "scb", "name": "Scheduled Commercial Bank", "regulator": "rbi"},
    {"canonical_key": "sfb", "name": "Small Finance Bank", "regulator": "rbi"},
    {"canonical_key": "payments_bank", "name": "Payments Bank", "regulator": "rbi"},
    {"canonical_key": "cooperative_bank", "name": "Cooperative Bank", "regulator": "rbi"},
    {"canonical_key": "nbfc", "name": "Non-Banking Financial Company", "regulator": "rbi"},
    {"canonical_key": "nbfc_mfi", "name": "NBFC - Microfinance Institution", "regulator": "rbi"},
    {
        "canonical_key": "nbfc_icc",
        "name": "NBFC - Investment and Credit Company",
        "regulator": "rbi",
    },
    {"canonical_key": "hfc", "name": "Housing Finance Company", "regulator": "rbi"},
    {"canonical_key": "payment_aggregator", "name": "Payment Aggregator", "regulator": "rbi"},
    {"canonical_key": "pso", "name": "Payment System Operator", "regulator": "rbi"},
    {
        "canonical_key": "ppi_issuer",
        "name": "Prepaid Payment Instrument Issuer",
        "regulator": "rbi",
    },
    {"canonical_key": "arc", "name": "Asset Reconstruction Company", "regulator": "rbi"},
    {"canonical_key": "cic", "name": "Credit Information Company", "regulator": "rbi"},
    {"canonical_key": "primary_dealer", "name": "Primary Dealer", "regulator": "rbi"},
    {
        "canonical_key": "account_aggregator",
        "name": "Account Aggregator (NBFC-AA)",
        "regulator": "rbi",
    },
    {
        "canonical_key": "nbfc_p2p",
        "name": "NBFC - Peer to Peer Lending Platform",
        "regulator": "rbi",
    },
    {"canonical_key": "nbfc_factor", "name": "NBFC - Factor", "regulator": "rbi"},
    {"canonical_key": "cic_core", "name": "Core Investment Company", "regulator": "rbi"},
    {"canonical_key": "white_label_atm", "name": "White Label ATM Operator", "regulator": "rbi"},
    {"canonical_key": "ffmc", "name": "Full-Fledged Money Changer", "regulator": "rbi"},
    {
        "canonical_key": "lending_service_provider",
        "name": "Lending Service Provider",
        "regulator": "rbi",
    },
    {"canonical_key": "aif", "name": "Alternative Investment Fund", "regulator": "sebi"},
    {"canonical_key": "mutual_fund", "name": "Mutual Fund", "regulator": "sebi"},
    {"canonical_key": "amc", "name": "Asset Management Company", "regulator": "sebi"},
    {"canonical_key": "fpi", "name": "Foreign Portfolio Investor", "regulator": "sebi"},
    {"canonical_key": "stock_broker", "name": "Stock Broker", "regulator": "sebi"},
    {
        "canonical_key": "depository_participant",
        "name": "Depository Participant",
        "regulator": "sebi",
    },
    {
        "canonical_key": "investment_adviser",
        "name": "Registered Investment Adviser",
        "regulator": "sebi",
    },
    {"canonical_key": "research_analyst", "name": "Research Analyst", "regulator": "sebi"},
    {"canonical_key": "portfolio_manager", "name": "Portfolio Manager", "regulator": "sebi"},
    {"canonical_key": "merchant_banker", "name": "Merchant Banker", "regulator": "sebi"},
    {"canonical_key": "credit_rating_agency", "name": "Credit Rating Agency", "regulator": "sebi"},
    {"canonical_key": "debenture_trustee", "name": "Debenture Trustee", "regulator": "sebi"},
    {"canonical_key": "custodian", "name": "Custodian of Securities", "regulator": "sebi"},
    {"canonical_key": "reit", "name": "Real Estate Investment Trust", "regulator": "sebi"},
    {"canonical_key": "invit", "name": "Infrastructure Investment Trust", "regulator": "sebi"},
    {"canonical_key": "stock_exchange", "name": "Stock Exchange", "regulator": "sebi"},
    {"canonical_key": "clearing_corporation", "name": "Clearing Corporation", "regulator": "sebi"},
    {"canonical_key": "depository", "name": "Depository", "regulator": "sebi"},
    {"canonical_key": "life_insurer", "name": "Life Insurer", "regulator": "irdai"},
    {"canonical_key": "general_insurer", "name": "General Insurer", "regulator": "irdai"},
    {"canonical_key": "health_insurer", "name": "Standalone Health Insurer", "regulator": "irdai"},
    {"canonical_key": "reinsurer", "name": "Reinsurer", "regulator": "irdai"},
    {"canonical_key": "insurance_broker", "name": "Insurance Broker", "regulator": "irdai"},
    {"canonical_key": "corporate_agent", "name": "Corporate Agent", "regulator": "irdai"},
    {
        "canonical_key": "insurance_web_aggregator",
        "name": "Insurance Web Aggregator",
        "regulator": "irdai",
    },
    {"canonical_key": "tpa", "name": "Third Party Administrator", "regulator": "irdai"},
    {"canonical_key": "private_company", "name": "Private Limited Company", "regulator": "mca"},
    {"canonical_key": "public_company", "name": "Public Limited Company", "regulator": "mca"},
    {"canonical_key": "llp", "name": "Limited Liability Partnership", "regulator": "mca"},
    {"canonical_key": "opc", "name": "One Person Company", "regulator": "mca"},
    {"canonical_key": "nidhi", "name": "Nidhi Company", "regulator": "mca"},
    {"canonical_key": "producer_company", "name": "Producer Company", "regulator": "mca"},
    {"canonical_key": "section_8_company", "name": "Section 8 Company", "regulator": "mca"},
    # Tax, trade and cyber classes — cut across the financial-sector entities above.
    {"canonical_key": "taxpayer", "name": "Taxpayer / Assessee", "regulator": "cbdt"},
    {"canonical_key": "tds_deductor", "name": "TDS Deductor", "regulator": "cbdt"},
    {"canonical_key": "reporting_entity", "name": "Reporting Entity (SFT)", "regulator": "cbdt"},
    {
        "canonical_key": "gst_registered_entity",
        "name": "GST-Registered Entity",
        "regulator": "cbic",
    },
    {"canonical_key": "importer_exporter", "name": "Importer / Exporter", "regulator": "cbic"},
    {"canonical_key": "exporter", "name": "Exporter (IEC holder)", "regulator": "dgft"},
    {"canonical_key": "body_corporate", "name": "Body Corporate (IT Act)", "regulator": "meity"},
    {"canonical_key": "intermediary", "name": "Intermediary (IT Act)", "regulator": "meity"},
    {"canonical_key": "data_fiduciary", "name": "Data Fiduciary (DPDP Act)", "regulator": "meity"},
    {
        "canonical_key": "service_provider_certin",
        "name": "Service Provider / Body Corporate",
        "regulator": "certin",
    },
    {
        "canonical_key": "pmla_reporting_entity",
        "name": "Reporting Entity (PMLA)",
        "regulator": "fiu_ind",
    },
    # Pension sector (PFRDA) and IFSC / GIFT-City (IFSCA) — added to widen
    # compliance-mapping coverage to these regulators' regulated entities.
    {"canonical_key": "pension_fund", "name": "Pension Fund (NPS)", "regulator": "pfrda"},
    {"canonical_key": "point_of_presence", "name": "Point of Presence (PoP)", "regulator": "pfrda"},
    {
        "canonical_key": "central_recordkeeping_agency",
        "name": "Central Recordkeeping Agency (CRA)",
        "regulator": "pfrda",
    },
    {"canonical_key": "ifsc_banking_unit", "name": "IFSC Banking Unit (IBU)", "regulator": "ifsca"},
    {"canonical_key": "ifsc_unit", "name": "IFSC Registered Unit", "regulator": "ifsca"},
    {
        "canonical_key": "ifsc_fund_management",
        "name": "Fund Management Entity (IFSC)",
        "regulator": "ifsca",
    },
    {"canonical_key": "npci_member", "name": "NPCI Member / Participant", "regulator": "npci"},
]

PARENT_ACTS: list[dict] = [
    {
        "canonical_key": "rbi_act_1934",
        "name": "Reserve Bank of India Act, 1934",
        "year": 1934,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "banking_regulation_act_1949",
        "name": "Banking Regulation Act, 1949",
        "year": 1949,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "sebi_act_1992",
        "name": "Securities and Exchange Board of India Act, 1992",
        "year": 1992,
        "anchors_regulator": "sebi",
    },
    {
        "canonical_key": "scra_1956",
        "name": "Securities Contracts (Regulation) Act, 1956",
        "year": 1956,
        "anchors_regulator": "sebi",
    },
    {
        "canonical_key": "pss_act_2007",
        "name": "Payment and Settlement Systems Act, 2007",
        "year": 2007,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "insurance_act_1938",
        "name": "Insurance Act, 1938",
        "year": 1938,
        "anchors_regulator": "irdai",
    },
    {
        "canonical_key": "irda_act_1999",
        "name": "Insurance Regulatory and Development Authority Act, 1999",
        "year": 1999,
        "anchors_regulator": "irdai",
    },
    {
        "canonical_key": "companies_act_2013",
        "name": "Companies Act, 2013",
        "year": 2013,
        "anchors_regulator": "mca",
    },
    {
        "canonical_key": "llp_act_2008",
        "name": "Limited Liability Partnership Act, 2008",
        "year": 2008,
        "anchors_regulator": "mca",
    },
    {
        "canonical_key": "fema_1999",
        "name": "Foreign Exchange Management Act, 1999",
        "year": 1999,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "pmla_2002",
        "name": "Prevention of Money-Laundering Act, 2002",
        "year": 2002,
        "anchors_regulator": "fiu_ind",
    },
    {
        "canonical_key": "cica_2005",
        "name": "Credit Information Companies (Regulation) Act, 2005",
        "year": 2005,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "factoring_act_2011",
        "name": "Factoring Regulation Act, 2011",
        "year": 2011,
        "anchors_regulator": "rbi",
    },
    {
        "canonical_key": "depositories_act_1996",
        "name": "Depositories Act, 1996",
        "year": 1996,
        "anchors_regulator": "sebi",
    },
    {
        "canonical_key": "income_tax_act_1961",
        "name": "Income-tax Act, 1961",
        "year": 1961,
        "anchors_regulator": "cbdt",
    },
    {
        "canonical_key": "cgst_act_2017",
        "name": "Central Goods and Services Tax Act, 2017",
        "year": 2017,
        "anchors_regulator": "cbic",
    },
    {
        "canonical_key": "customs_act_1962",
        "name": "Customs Act, 1962",
        "year": 1962,
        "anchors_regulator": "cbic",
    },
    {
        "canonical_key": "it_act_2000",
        "name": "Information Technology Act, 2000",
        "year": 2000,
        "anchors_regulator": "meity",
    },
    {
        "canonical_key": "dpdp_act_2023",
        "name": "Digital Personal Data Protection Act, 2023",
        "year": 2023,
        "anchors_regulator": "meity",
    },
    {
        "canonical_key": "ftdr_act_1992",
        "name": "Foreign Trade (Development and Regulation) Act, 1992",
        "year": 1992,
        "anchors_regulator": "dgft",
    },
]

# Crawl targets for the monitoring agent. ``scraper_kind`` selects the scraper
# implementation in ``policyai_scrapers``; cadence is hours between crawls.
MONITORING_SOURCES: list[dict] = [
    {
        "regulator_key": "rbi",
        "name": "RBI — Notifications",
        "base_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        "scraper_kind": "rbi_notifications",
        "cadence_hours": 6,
    },
    {
        "regulator_key": "sebi",
        "name": "SEBI — Master Circulars",
        "base_url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=6&smid=0",
        "scraper_kind": "sebi_circulars",
        "cadence_hours": 6,
    },
    {
        "regulator_key": "sebi",
        "name": "SEBI — Circulars",
        "base_url": "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0",
        "scraper_kind": "sebi_general_circulars",
        "cadence_hours": 6,
    },
    {
        "regulator_key": "irdai",
        "name": "IRDAI — Circulars",
        "base_url": "https://irdai.gov.in/circulars",
        "scraper_kind": "irdai_circulars",
        "cadence_hours": 12,
    },
    {
        "regulator_key": "mca",
        "name": "MCA — Notifications",
        "base_url": "https://www.mca.gov.in/content/mca/global/en/acts-rules-prospect/notifications.html",
        "scraper_kind": "mca_notifications",
        "cadence_hours": 24,
        # MCA sits behind Akamai bot protection (403 even for a real headless
        # browser). Disabled here; MCA notifications are instead picked up via the
        # eGazette feed below (authoritative copies, no bot wall).
        "enabled": False,
    },
    # --- Lightweight RSS/Atom feed sources (httpx, no browser) -------------
    # These broaden coverage to tax / trade / cyber / gazette. Confirm each feed
    # URL against the live endpoint before enabling — the FeedScraper records a
    # failed scan (and skips) if a URL is wrong, so a bad URL is safe but silent.
    {
        "regulator_key": "rbi",
        "name": "RBI — Press Releases (RSS)",
        "base_url": "https://www.rbi.org.in/Scripts/RSS.aspx",
        "scraper_kind": "rbi_press_rss",
        "cadence_hours": 6,
        "enabled": False,  # verify RBI RSS endpoint
    },
    {
        "regulator_key": "pib",
        "name": "PIB — Policy Announcements (RSS)",
        "base_url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
        "scraper_kind": "pib_rss",
        "cadence_hours": 12,
        "enabled": False,  # verify PIB ministry RSS params
    },
    {
        "regulator_key": "certin",
        "name": "CERT-In — Advisories (RSS)",
        "base_url": "https://www.cert-in.org.in/RSSFeeds.jsp",
        "scraper_kind": "certin_rss",
        "cadence_hours": 12,
        "enabled": False,  # verify CERT-In RSS endpoint
    },
    {
        "regulator_key": "cbic",
        "name": "CBIC — GST / Customs (RSS)",
        "base_url": "https://www.cbic.gov.in/entities/view-rss",
        "scraper_kind": "cbic_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify CBIC RSS endpoint
    },
    {
        "regulator_key": "cbdt",
        "name": "CBDT — Direct Tax (RSS)",
        "base_url": "https://incometaxindia.gov.in/_layouts/15/dit/pages/rss.aspx",
        "scraper_kind": "cbdt_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify CBDT RSS endpoint
    },
    {
        "regulator_key": "dgft",
        "name": "DGFT — Trade Notifications (RSS)",
        "base_url": "https://www.dgft.gov.in/CP/?opt=rss",
        "scraper_kind": "dgft_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify DGFT RSS endpoint
    },
    {
        "regulator_key": "egazette",
        "name": "eGazette — Acts/Rules (incl. MCA)",
        "base_url": "https://egazette.gov.in/(S())/rss.aspx",
        "scraper_kind": "egazette_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify eGazette RSS endpoint
    },
    # --- Newly added BFSI regulators. Seeded disabled until each feed URL is
    # verified against the live endpoint (same convention as the feeds above). The
    # regulator + entity-class vocabulary they reference is already seeded, so even
    # before crawling is enabled, documents from these bodies classify correctly.
    {
        "regulator_key": "pfrda",
        "name": "PFRDA — Circulars (RSS)",
        "base_url": "https://www.pfrda.org.in/rss",
        "scraper_kind": "pfrda_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify PFRDA feed/listing endpoint
    },
    {
        "regulator_key": "ifsca",
        "name": "IFSCA — Circulars (RSS)",
        "base_url": "https://ifsca.gov.in/rss",
        "scraper_kind": "ifsca_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify IFSCA feed/listing endpoint
    },
    {
        "regulator_key": "npci",
        "name": "NPCI — Circulars (RSS)",
        "base_url": "https://www.npci.org.in/rss",
        "scraper_kind": "npci_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify NPCI feed/listing endpoint
    },
    {
        "regulator_key": "fiu_ind",
        "name": "FIU-IND — Directions (RSS)",
        "base_url": "https://fiuindia.gov.in/rss",
        "scraper_kind": "fiu_rss",
        "cadence_hours": 24,
        "enabled": False,  # verify FIU-IND feed/listing endpoint
    },
]


async def _get_or_create_monitoring_source(session: AsyncSession, spec: dict) -> MonitoringSource:
    stmt = select(MonitoringSource).where(
        MonitoringSource.regulator_key == spec["regulator_key"],
        MonitoringSource.scraper_kind == spec["scraper_kind"],
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing
    source = MonitoringSource(
        regulator_key=spec["regulator_key"],
        name=spec["name"],
        base_url=spec["base_url"],
        scraper_kind=spec["scraper_kind"],
        cadence_hours=spec["cadence_hours"],
        enabled=spec.get("enabled", True),
    )
    session.add(source)
    await session.flush()
    return source


async def seed(session: AsyncSession) -> dict[str, int]:
    """Insert canonical data. Idempotent. Returns counts by node type."""
    regulator_by_key: dict[str, Node] = {}

    for reg in REGULATORS:
        parent = await _get_or_create_node(
            session,
            node_type=NodeType.REGULATOR,
            canonical_key=reg["canonical_key"],
            properties={
                "canonical_key": reg["canonical_key"],
                "name": reg["name"],
                "short_name": reg["short_name"],
                "kind": reg["kind"],
                "is_root": True,
            },
        )
        regulator_by_key[reg["canonical_key"]] = parent
        for dept in reg["departments"]:
            child = await _get_or_create_node(
                session,
                node_type=NodeType.REGULATOR,
                canonical_key=dept["canonical_key"],
                properties={
                    "canonical_key": dept["canonical_key"],
                    "name": dept["name"],
                    "short_name": dept["short_name"],
                    "kind": "department",
                    "parent_regulator": reg["canonical_key"],
                    "is_root": False,
                },
            )
            await _get_or_create_edge(
                session, source=child, target=parent, edge_type=EdgeType.ISSUED_BY
            )

    for ec in ENTITY_CLASSES:
        node = await _get_or_create_node(
            session,
            node_type=NodeType.ENTITY_CLASS,
            canonical_key=ec["canonical_key"],
            properties={
                "canonical_key": ec["canonical_key"],
                "name": ec["name"],
                "regulator": ec["regulator"],
            },
        )
        regulator = regulator_by_key[ec["regulator"]]
        await _get_or_create_edge(
            session, source=node, target=regulator, edge_type=EdgeType.ISSUED_BY
        )

    for act in PARENT_ACTS:
        node = await _get_or_create_node(
            session,
            node_type=NodeType.PARENT_ACT,
            canonical_key=act["canonical_key"],
            properties={
                "canonical_key": act["canonical_key"],
                "name": act["name"],
                "year": act["year"],
                "anchors_regulator": act["anchors_regulator"],
            },
        )
        regulator = regulator_by_key[act["anchors_regulator"]]
        await _get_or_create_edge(
            session, source=regulator, target=node, edge_type=EdgeType.DERIVED_FROM
        )

    for spec in MONITORING_SOURCES:
        await _get_or_create_monitoring_source(session, spec)

    await session.commit()

    counts: dict[str, int] = {}
    for nt in NodeType:
        result = await session.execute(select(Node).where(Node.node_type == nt.value))
        counts[nt.value] = len(result.scalars().all())
    sources = await session.execute(select(MonitoringSource))
    counts["monitoring_source"] = len(sources.scalars().all())
    return counts


async def _main() -> None:
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        counts = await seed(session)
    print("Seed complete. Node counts:")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
