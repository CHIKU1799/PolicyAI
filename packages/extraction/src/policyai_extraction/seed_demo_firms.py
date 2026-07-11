"""Seed several demo firms (tenants) with distinct profiles and policy documents.

Gives the platform real multi-company data so the admin console has more than one
org to visualise: each firm gets its own Organization, a CompanyProfile (entity
classes / topics / regulators that drive the relevance gate), and one policy
document of its own (embedded for gap analysis). Idempotent on org slug and on
document content_hash.

    make seed-firms                 # create orgs + profiles + policies (no LLM)
    make seed-firms ARGS=--map      # also map each org's obligations/gaps (uses LLM)

Mapping is per-org and gated by each firm's profile, so an NBFC and an AIF get
different obligations from the same shared regulation graph.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
from uuid import UUID, uuid4

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.models_app import (
    CompanyDocument,
    CompanyProfile,
    DocumentStatus,
    Organization,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction.embeddings import embed_text
from policyai_extraction.llm import LLMClient

log = logging.getLogger("policyai.seed_firms")

# Each firm: a name, a slug, an applicability profile, and one of its own policies.
FIRMS = [
    {
        "name": "Acme Finance Ltd.",
        "slug": "acme-finance",
        "entity_classes": ["nbfc", "pmla_reporting_entity"],
        "topics": ["kyc", "fair_practices_code", "outsourcing", "grievance_redressal"],
        "regulators": ["rbi"],
        "policy_name": "KYC and AML Policy.txt",
        "policy_text": (
            "KYC AND ANTI-MONEY-LAUNDERING POLICY. Acme Finance Ltd. shall verify the "
            "identity of every customer at onboarding using officially valid documents "
            "and shall carry out customer due diligence for all accounts. The company "
            "maintains records of transactions for a minimum period of five years. A "
            "designated Principal Officer files Suspicious Transaction Reports and Cash "
            "Transaction Reports with FIU-IND. Periodic re-KYC is undertaken for higher "
            "risk customers. The policy does not currently address sanctions screening "
            "against UNSC lists or a documented risk-categorisation framework."
        ),
    },
    {
        "name": "Beacon Capital AIF",
        "slug": "beacon-capital",
        "entity_classes": ["aif", "portfolio_manager"],
        "topics": ["disclosure", "valuation", "grievance_redressal", "conflict_of_interest"],
        "regulators": ["sebi"],
        "policy_name": "Investor Disclosure Policy.txt",
        "policy_text": (
            "INVESTOR DISCLOSURE AND VALUATION POLICY. Beacon Capital AIF provides each "
            "investor a private placement memorandum before commitment and reports the "
            "net asset value of the scheme on a quarterly basis. Material changes to the "
            "fund's terms are disclosed to all investors. Valuation of portfolio "
            "investments follows an independent valuer's assessment at least annually. "
            "The policy is silent on the timeline for reporting conflicts of interest and "
            "on the grievance-redressal escalation matrix required for investors."
        ),
    },
    {
        "name": "Sowmya Microfinance",
        "slug": "sowmya-mfi",
        "entity_classes": ["nbfc_mfi", "pmla_reporting_entity"],
        "topics": ["fair_practices_code", "pricing", "grievance_redressal", "kyc"],
        "regulators": ["rbi"],
        "policy_name": "Fair Practices and Pricing Policy.txt",
        "policy_text": (
            "FAIR PRACTICES AND PRICING POLICY. Sowmya Microfinance discloses the all-in "
            "effective interest rate and processing fees to every borrower in the loan "
            "card in the vernacular language. There is no prepayment penalty on "
            "microfinance loans. A board-approved policy governs the limit on the maximum "
            "repayment obligation of a household as a percentage of household income. "
            "Recovery is carried out only at designated centrally-designated places. The "
            "policy does not yet document the cooling-off period or a published grievance "
            "redressal officer for the nodal RBI ombudsman scheme."
        ),
    },
]


async def _seed_firm(session: AsyncSession, firm: dict) -> tuple[UUID, bool]:
    """Create the org + profile + policy for one firm. Returns (org_id, created)."""
    org = (
        await session.execute(select(Organization).where(Organization.slug == firm["slug"]))
    ).scalar_one_or_none()
    created = org is None
    if org is None:
        org = Organization(id=uuid4(), name=firm["name"], slug=firm["slug"])
        session.add(org)
        await session.flush()

    # Profile (unique per org) drives the relevance gate.
    profile = (
        await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == org.id))
    ).scalar_one_or_none()
    if profile is None:
        profile = CompanyProfile(org_id=org.id)
        session.add(profile)
    profile.entity_classes = firm["entity_classes"]
    profile.topics = firm["topics"]
    profile.regulators = firm["regulators"]
    profile.notes = f"Seeded demo firm: {firm['name']}"

    # The firm's own policy document, embedded for gap analysis.
    text = firm["policy_text"]
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    doc = (
        await session.execute(
            select(CompanyDocument).where(
                CompanyDocument.org_id == org.id,
                CompanyDocument.content_hash == content_hash,
            )
        )
    ).scalar_one_or_none()
    if doc is None or doc.embedding is None:
        embedding = await embed_text(text[:8000])
        doc = doc or CompanyDocument(org_id=org.id)
        doc.storage_path = f"seed/{firm['slug']}/{firm['policy_name']}"
        doc.filename = firm["policy_name"]
        doc.mime = "text/plain"
        doc.raw_text = text
        doc.embedding = embedding
        doc.content_hash = content_hash
        doc.status = DocumentStatus.PROCESSED.value
        session.add(doc)

    await session.commit()
    return org.id, created


async def _run(do_map: bool) -> None:
    engine = make_engine()
    sm = make_sessionmaker(engine)
    llm = LLMClient()
    try:
        async with sm() as session:
            for firm in FIRMS:
                org_id, created = await _seed_firm(session, firm)
                log.info(
                    "%s firm %s (org %s)",
                    "created" if created else "updated",
                    firm["name"],
                    str(org_id),
                )
                if do_map:
                    from policyai_extraction.map_all import map_unmapped_in_session

                    mapped, skipped = await map_unmapped_in_session(session, llm, org_id=org_id)
                    log.info("  mapped=%d skipped=%d for %s", mapped, skipped, firm["name"])
        if do_map:
            log.info("LLM cost: %s", llm.cost.summary())
    finally:
        await llm.aclose()
        await engine.dispose()


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed demo firms (orgs + profiles + policies).")
    ap.add_argument("--map", action="store_true", dest="do_map", help="also map obligations/gaps")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(_run(args.do_map))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
