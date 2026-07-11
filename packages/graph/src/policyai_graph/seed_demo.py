"""Demo data so the dashboard shows a full end-to-end slice before the first live
crawl — a sample RBI/NBFC-MFI regulation, a company profile, and the obligation +
tasks + alerts it produces. Idempotent: safe to re-run. Requires the canonical
``seed`` to have run first (it reuses the seeded rbi/nbfc_mfi nodes).

    uv run python -m policyai_graph.seed_demo
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_graph.db import make_engine, make_sessionmaker
from policyai_graph.graph_ops import find_node, get_or_create_edge, get_or_create_node
from policyai_graph.models import EdgeType, NodeType
from policyai_graph.models_app import (
    DEFAULT_ORG_ID,
    Alert,
    AlertKind,
    CompanyDocument,
    CompanyProfile,
    Control,
    ControlTest,
    ControlType,
    DocumentStatus,
    Effectiveness,
    Gap,
    GapStatus,
    Obligation,
    ObligationControl,
    ObligationPolicy,
    Policy,
    PolicyStatus,
    PolicyVersion,
    Priority,
    Severity,
    Task,
    TestResult,
)

DEMO_REG_KEY = "rbi:demo-mfi-pricing-2026"
DEMO_COMPANY = "Demo Microfinance Co."
DEMO_TOPICS = ["pricing_cap", "fair_practices_code", "kyc"]


async def seed_demo(session: AsyncSession) -> dict[str, int]:
    # 1) A sample regulation node + its edges (reusing seeded rbi / nbfc_mfi).
    reg = await get_or_create_node(
        session,
        node_type=NodeType.REGULATION,
        canonical_key=DEMO_REG_KEY,
        properties={
            "canonical_key": DEMO_REG_KEY,
            "title": "Master Direction — Pricing of Microfinance Loans (Demo)",
            "summary": (
                "Caps the interest spread on microfinance loans and tightens "
                "fair-practices and KYC disclosure for NBFC-MFIs."
            ),
            "regulator": "rbi",
            "severity": Severity.HIGH.value,
            "source_url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
            "published_date": "2026-06-15",
        },
    )
    dor = await find_node(session, node_type=NodeType.REGULATOR, canonical_key="rbi.dor")
    if dor is not None:
        await get_or_create_edge(session, source=reg, target=dor, edge_type=EdgeType.ISSUED_BY)
    nbfc_mfi = await find_node(session, node_type=NodeType.ENTITY_CLASS, canonical_key="nbfc_mfi")
    if nbfc_mfi is not None:
        await get_or_create_edge(
            session, source=reg, target=nbfc_mfi, edge_type=EdgeType.APPLIES_TO
        )
    for topic in DEMO_TOPICS:
        node = await get_or_create_node(
            session,
            node_type=NodeType.TOPIC,
            canonical_key=topic,
            properties={"canonical_key": topic, "name": topic.replace("_", " ").title()},
        )
        await get_or_create_edge(session, source=reg, target=node, edge_type=EdgeType.COVERS_TOPIC)
    deadline = await get_or_create_node(
        session,
        node_type=NodeType.DEADLINE,
        canonical_key=f"{DEMO_REG_KEY}:deadline",
        properties={
            "canonical_key": f"{DEMO_REG_KEY}:deadline",
            "description": "Comply with revised pricing caps",
            "due_date": "2026-09-30",
        },
    )
    await get_or_create_edge(session, source=reg, target=deadline, edge_type=EdgeType.HAS_DEADLINE)
    await session.flush()

    # 2) Company profile for the default org.
    profile = (
        await session.execute(select(CompanyProfile).where(CompanyProfile.org_id == DEFAULT_ORG_ID))
    ).scalar_one_or_none()
    if profile is None:
        profile = CompanyProfile(org_id=DEFAULT_ORG_ID)
        session.add(profile)
    profile.entity_classes = ["nbfc_mfi"]
    profile.topics = DEMO_TOPICS
    profile.regulators = ["rbi"]
    profile.notes = DEMO_COMPANY

    # 3) A sample uploaded policy doc.
    if not (
        await session.execute(
            select(CompanyDocument).where(
                CompanyDocument.org_id == DEFAULT_ORG_ID,
                CompanyDocument.content_hash == "demo-fair-practices",
            )
        )
    ).scalar_one_or_none():
        session.add(
            CompanyDocument(
                org_id=DEFAULT_ORG_ID,
                storage_path="demo/fair-practices-code.pdf",
                filename="Fair Practices Code.pdf",
                mime="application/pdf",
                raw_text=(
                    "Our Fair Practices Code sets interest pricing by board policy and "
                    "discloses the effective rate to borrowers. KYC is refreshed every 24 months."
                ),
                content_hash="demo-fair-practices",
                status=DocumentStatus.PROCESSED.value,
            )
        )

    # 4) The obligation this regulation creates for the company.
    obligation = (
        await session.execute(
            select(Obligation).where(
                Obligation.org_id == DEFAULT_ORG_ID,
                Obligation.regulation_node_id == reg.id,
            )
        )
    ).scalar_one_or_none()
    if obligation is None:
        obligation = Obligation(org_id=DEFAULT_ORG_ID, regulation_node_id=reg.id)
        session.add(obligation)
    obligation.title = "Align microfinance pricing with revised RBI caps"
    obligation.summary = (
        "As an NBFC-MFI, the company must cap its interest spread per the new Master "
        "Direction and update borrower disclosures accordingly."
    )
    obligation.what_changed = (
        "Introduces an explicit spread cap and quarterly disclosure of the average "
        "effective rate — previously left to board policy."
    )
    obligation.gap_analysis = (
        "The company's Fair Practices Code sets pricing by board policy and refreshes "
        "KYC every 24 months. Gaps: no explicit spread cap, and no quarterly effective-rate "
        "disclosure as now required."
    )
    obligation.severity = Severity.HIGH.value
    await session.flush()

    # 5) Tasks (only if none exist yet for this obligation).
    has_tasks = (
        await session.execute(
            select(func.count()).select_from(Task).where(Task.obligation_id == obligation.id)
        )
    ).scalar_one()
    if not has_tasks:
        demo_tasks = [
            (
                "Recompute loan pricing against the new spread cap",
                Priority.URGENT,
                "Head of Credit",
            ),
            (
                "Add quarterly effective-rate disclosure to borrower statements",
                Priority.HIGH,
                "Compliance Officer",
            ),
            (
                "Update the Fair Practices Code and re-circulate to branches",
                Priority.MEDIUM,
                "Compliance Officer",
            ),
        ]
        for title, prio, owner in demo_tasks:
            session.add(
                Task(
                    org_id=DEFAULT_ORG_ID,
                    obligation_id=obligation.id,
                    title=title,
                    owner=owner,
                    priority=prio.value,
                    due_date=date(2026, 9, 30),
                )
            )

    # 5b) GRC demo — controls + tests, a versioned policy, a gap, and the
    # obligation→control/policy mappings that make the obligation "structured".
    has_controls = (
        await session.execute(
            select(func.count()).select_from(Control).where(Control.org_id == DEFAULT_ORG_ID)
        )
    ).scalar_one()
    if not has_controls:
        controls = [
            Control(
                org_id=DEFAULT_ORG_ID,
                ref_code="C-001",
                title="Interest spread cap monitoring",
                description="Monthly check that loan pricing stays within the RBI spread cap.",
                control_type=ControlType.DETECTIVE.value,
                frequency="monthly",
                owner="Head of Credit",
                effectiveness=Effectiveness.EFFECTIVE.value,
            ),
            Control(
                org_id=DEFAULT_ORG_ID,
                ref_code="C-002",
                title="Periodic KYC refresh",
                description="KYC re-verification on the prescribed cadence.",
                control_type=ControlType.PREVENTIVE.value,
                frequency="annual",
                owner="Compliance Officer",
                effectiveness=Effectiveness.PARTIAL.value,
            ),
            Control(
                org_id=DEFAULT_ORG_ID,
                ref_code="C-003",
                title="Effective-rate disclosure",
                description="Borrower statements disclose the effective annualised rate.",
                control_type=ControlType.PREVENTIVE.value,
                frequency="per-disbursal",
                owner="Operations",
                effectiveness=Effectiveness.UNTESTED.value,
            ),
        ]
        for c in controls:
            session.add(c)
        await session.flush()
        session.add(
            ControlTest(
                org_id=DEFAULT_ORG_ID,
                control_id=controls[0].id,
                performed_at=datetime(2026, 6, 1, tzinfo=UTC),
                performed_by="Internal Audit",
                result=TestResult.PASS.value,
                notes="Spread within cap for all sampled loans.",
            )
        )
        session.add(
            ControlTest(
                org_id=DEFAULT_ORG_ID,
                control_id=controls[1].id,
                performed_at=datetime(2026, 5, 15, tzinfo=UTC),
                performed_by="Internal Audit",
                result=TestResult.FAIL.value,
                notes="12% of accounts overdue for KYC refresh.",
            )
        )
        for c in controls:
            session.add(
                ObligationControl(
                    org_id=DEFAULT_ORG_ID, obligation_id=obligation.id, control_id=c.id
                )
            )

    has_policy = (
        await session.execute(
            select(func.count()).select_from(Policy).where(Policy.org_id == DEFAULT_ORG_ID)
        )
    ).scalar_one()
    if not has_policy:
        policy = Policy(
            org_id=DEFAULT_ORG_ID,
            title="Fair Practices Code",
            summary="Pricing, disclosure and grievance-redressal policy for microfinance lending.",
            owner="Compliance Officer",
            status=PolicyStatus.APPROVED.value,
            current_version=2,
        )
        session.add(policy)
        await session.flush()
        session.add(
            PolicyVersion(
                policy_id=policy.id,
                version_no=1,
                change_note="Initial version.",
                status=PolicyStatus.ARCHIVED.value,
                created_by="Compliance Officer",
                approved_by="Board",
                approved_at=datetime(2025, 4, 1, tzinfo=UTC),
            )
        )
        session.add(
            PolicyVersion(
                policy_id=policy.id,
                version_no=2,
                change_note="Added effective-rate disclosure clause.",
                status=PolicyStatus.APPROVED.value,
                created_by="Compliance Officer",
                approved_by="Board",
                approved_at=datetime(2026, 3, 15, tzinfo=UTC),
            )
        )
        session.add(
            ObligationPolicy(
                org_id=DEFAULT_ORG_ID, obligation_id=obligation.id, policy_id=policy.id
            )
        )

    has_gap = (
        await session.execute(
            select(func.count()).select_from(Gap).where(Gap.obligation_id == obligation.id)
        )
    ).scalar_one()
    if not has_gap:
        session.add(
            Gap(
                org_id=DEFAULT_ORG_ID,
                obligation_id=obligation.id,
                description=(
                    "No explicit spread-cap evidence for the latest quarter; the KYC refresh "
                    "control is failing for 12% of accounts."
                ),
                severity=Severity.HIGH.value,
                status=GapStatus.OPEN.value,
                remediation_plan=(
                    "Automate spread-cap monitoring and clear the KYC refresh backlog by Q3."
                ),
                owner="Compliance Officer",
                due_date=date(2026, 9, 30),
            )
        )

    # 6) Alerts (only seed once).
    has_alerts = (
        await session.execute(
            select(func.count()).select_from(Alert).where(Alert.org_id == DEFAULT_ORG_ID)
        )
    ).scalar_one()
    if not has_alerts:
        session.add(
            Alert(
                org_id=DEFAULT_ORG_ID,
                kind=AlertKind.NEW_REGULATION.value,
                regulation_node_id=reg.id,
                message="New RBI regulation: Pricing of Microfinance Loans (Demo)",
            )
        )
        session.add(
            Alert(
                org_id=DEFAULT_ORG_ID,
                kind=AlertKind.NEW_OBLIGATION.value,
                regulation_node_id=reg.id,
                obligation_id=obligation.id,
                message="New obligation (high): Align microfinance pricing with revised RBI caps",
            )
        )

    await session.commit()

    counts = {
        "obligations": (
            await session.execute(
                select(func.count())
                .select_from(Obligation)
                .where(Obligation.org_id == DEFAULT_ORG_ID)
            )
        ).scalar_one(),
        "tasks": (
            await session.execute(
                select(func.count()).select_from(Task).where(Task.org_id == DEFAULT_ORG_ID)
            )
        ).scalar_one(),
        "alerts": (
            await session.execute(
                select(func.count()).select_from(Alert).where(Alert.org_id == DEFAULT_ORG_ID)
            )
        ).scalar_one(),
    }
    return counts


async def _main() -> None:
    engine = make_engine()
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as session:
        counts = await seed_demo(session)
    print("Demo seed complete:", counts)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
