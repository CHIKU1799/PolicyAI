"""Company-profile derivation, shared by the /profile/derive route and the
post-upload background hook so a fresh firm becomes mappable without any
manual step: upload a policy -> profile derived -> obligations mapped."""

from __future__ import annotations

import logging
import os
from uuid import UUID

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.graph_ops import find_node
from policyai_graph.models import NodeType
from policyai_graph.models_app import CompanyDocument, CompanyProfile, Organization
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_extraction import gbrain_client
from policyai_extraction.llm import MODEL_MAPPING, LLMClient
from policyai_extraction.map_all import map_unmapped_in_session
from policyai_extraction.pipeline import load_prompt
from policyai_extraction.schemas import CompanyProfileExtraction

log = logging.getLogger("policyai.profile")


async def valid_entity_classes(session: AsyncSession, keys: list[str]) -> list[str]:
    out: list[str] = []
    for k in keys:
        if await find_node(session, node_type=NodeType.ENTITY_CLASS, canonical_key=k):
            out.append(k)
    return out


async def derive_profile_in_session(
    session: AsyncSession,
    llm: LLMClient,
    org_id: UUID,
    company_name: str | None = None,
) -> CompanyProfile:
    """Run the company_profile prompt over the org's KB corpus and upsert the
    profile row. Caller owns the transaction."""
    docs = (
        (
            await session.execute(
                select(CompanyDocument).where(
                    CompanyDocument.org_id == org_id,
                    CompanyDocument.raw_text.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )
    corpus = "\n\n".join(f"[{d.filename}]\n{(d.raw_text or '')[:3000]}" for d in docs)

    gbrain_hint = ""
    if company_name and gbrain_client.is_configured():
        company = await gbrain_client.find_company(company_name)
        if company:
            gbrain_hint = f"\n\nGBRAIN MATCH (BFSI graph):\n{company}"

    extracted: CompanyProfileExtraction = await llm.extract(
        f"COMPANY DOCUMENTS:\n{corpus or '(none uploaded)'}{gbrain_hint}",
        CompanyProfileExtraction,
        system=load_prompt("company_profile_v1.md"),
        model=MODEL_MAPPING,
    )
    entity_classes = await valid_entity_classes(session, extracted.entity_classes)

    profile = (
        await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == org_id))
    ).scalar_one_or_none()
    if profile is None:
        profile = CompanyProfile(org_id=org_id)
        session.add(profile)
    profile.entity_classes = entity_classes
    profile.topics = extracted.topics
    profile.regulators = extracted.regulators
    if company_name:
        profile.notes = company_name
    await session.commit()
    # Stash the rationale on the instance for callers that want to report it.
    profile.__dict__["_rationale"] = extracted.rationale
    return profile


async def ensure_profile_and_map(org_id: UUID) -> None:
    """Post-upload background hook: derive the org's profile when missing, then
    run a bounded obligation-mapping pass so the firm's dashboard fills in
    without any manual trigger. Never raises (background task)."""
    if (os.getenv("MAP_AFTER_UPLOAD") or "1").lower() in ("0", "false", "off"):
        return
    limit = int(os.getenv("MAP_AFTER_UPLOAD_LIMIT") or "60")
    engine = make_engine()
    llm = LLMClient()
    try:
        async with make_sessionmaker(engine)() as session:
            profile = (
                await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == org_id))
            ).scalar_one_or_none()
            if profile is None or not profile.entity_classes:
                org = (
                    await session.execute(select(Organization).where(Organization.id == org_id))
                ).scalar_one_or_none()
                log.info("deriving missing profile for org %s", org_id)
                profile = await derive_profile_in_session(
                    session, llm, org_id, company_name=org.name if org else None
                )
            if profile.entity_classes:
                mapped, skipped = await map_unmapped_in_session(
                    session, llm, org_id=org_id, limit=limit
                )
                log.info(
                    "post-upload map for org %s: mapped=%d skipped=%d (limit %d)",
                    org_id,
                    mapped,
                    skipped,
                    limit,
                )
            else:
                log.info("org %s has no recognizable entity classes; mapping skipped", org_id)
    except Exception as exc:  # noqa: BLE001 - background task must not crash the worker
        log.warning("post-upload profile/map for org %s failed: %s", org_id, str(exc)[:300])
    finally:
        await llm.aclose()
        await engine.dispose()
