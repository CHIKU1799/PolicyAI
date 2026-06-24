"""Application tables for the compliance-intelligence platform.

These sit on top of the generic knowledge graph (``models.py``) and share the
same declarative ``Base`` so a single Alembic ``target_metadata`` sees them.

Tenancy: the MVP is single-org, but every table carries a nullable ``org_id``
so multi-tenant Auth + RLS can be retrofitted without a schema migration. A
single seeded organization row backfills these until then.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from policyai_graph.models import EMBEDDING_DIM, Base

# Sentinel org used while the platform is single-tenant. Real orgs replace this
# once Supabase Auth lands; the column stays nullable so nothing breaks meanwhile.
DEFAULT_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")


class ScanStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    NEEDS_OCR = "needs_ocr"
    FAILED = "failed"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ObligationStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    ADDRESSED = "addressed"
    DISMISSED = "dismissed"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(StrEnum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertKind(StrEnum):
    NEW_REGULATION = "new_regulation"
    NEW_OBLIGATION = "new_obligation"
    DEADLINE_APPROACHING = "deadline_approaching"
    SCAN_FAILED = "scan_failed"


class MonitoringSource(Base):
    """A regulator endpoint the agent crawls on a cadence."""

    __tablename__ = "monitoring_sources"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    regulator_key: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    scraper_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    cadence_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=6, server_default="6"
    )
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("regulator_key", "scraper_kind", name="uq_monitoring_source"),
    )


class ScanRun(Base):
    """One crawl of one source. The audit trail behind 'continuous monitoring'."""

    __tablename__ = "scan_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("monitoring_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ScanStatus.RUNNING.value
    )
    docs_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    docs_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanyDocument(Base):
    """A policy/registration doc the company uploaded into its knowledge base."""

    __tablename__ = "company_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=DocumentStatus.PENDING.value
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("org_id", "content_hash", name="uq_company_document_hash"),)


class CompanyProfile(Base):
    """The applicability fingerprint derived from a company's knowledge base.

    ``entity_classes``/``topics``/``regulators`` hold lists of canonical_keys that
    resolve to seeded graph nodes; obligation mapping intersects against them.
    """

    __tablename__ = "company_profiles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, unique=True)
    entity_classes: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    topics: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    regulators: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    derived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Obligation(Base):
    """A regulation's requirement as it applies to this company."""

    __tablename__ = "obligations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    regulation_node_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    what_changed: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default=Severity.MEDIUM.value)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ObligationStatus.OPEN.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("org_id", "regulation_node_id", name="uq_obligation_per_regulation"),
    )


class Task(Base):
    """A concrete action a human must take to satisfy an obligation."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    obligation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False
    )
    deadline_node_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("nodes.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default=Priority.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TaskStatus.TODO.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Alert(Base):
    """The notification feed surfaced in the dashboard via Supabase Realtime."""

    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    regulation_node_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True
    )
    obligation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ===========================================================================
# GRC core — Controls, Policies, Products, Gaps, audit trail, and the mappings
# that turn an obligation into something assigned to policies / controls /
# products / owners (the Zango-style "structured obligations" model).
# ===========================================================================


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"


class ControlType(StrEnum):
    PREVENTIVE = "preventive"
    DETECTIVE = "detective"
    CORRECTIVE = "corrective"


class Effectiveness(StrEnum):
    EFFECTIVE = "effective"
    PARTIAL = "partial"
    INEFFECTIVE = "ineffective"
    UNTESTED = "untested"


class TestResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class GapStatus(StrEnum):
    OPEN = "open"
    REMEDIATING = "remediating"
    CLOSED = "closed"
    ACCEPTED = "accepted"


class Policy(Base):
    """A logical policy in the central library. Content lives in PolicyVersion so
    the policy can be versioned with a review/approval lifecycle."""

    __tablename__ = "policies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PolicyStatus.DRAFT.value
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PolicyVersion(Base):
    """An immutable content snapshot of a policy + its review/approval state."""

    __tablename__ = "policy_versions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    policy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PolicyStatus.DRAFT.value
    )
    created_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("policy_id", "version_no", name="uq_policy_version"),)


class Control(Base):
    """A control the firm operates to satisfy obligations; its tested effectiveness."""

    __tablename__ = "controls"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    ref_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ControlType.PREVENTIVE.value
    )
    frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    effectiveness: Mapped[str] = mapped_column(
        String(16), nullable=False, default=Effectiveness.UNTESTED.value
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ControlTest(Base):
    """One test of a control's effectiveness, with result + evidence."""

    __tablename__ = "control_tests"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    control_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    performed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Product(Base):
    """A firm product/business line that obligations can apply to."""

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Gap(Base):
    """A gap between an obligation's requirement and the firm's coverage."""

    __tablename__ = "gaps"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    obligation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default=Severity.MEDIUM.value)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=GapStatus.OPEN.value)
    remediation_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    """Append-only audit trail for governance traceability. Never updated/deleted."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ObligationControl(Base):
    """Mapping: which controls satisfy an obligation."""

    __tablename__ = "obligation_controls"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    obligation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("obligation_id", "control_id", name="uq_obligation_control"),
    )


class ObligationPolicy(Base):
    """Mapping: which policies address an obligation."""

    __tablename__ = "obligation_policies"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    obligation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False
    )
    policy_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("obligation_id", "policy_id", name="uq_obligation_policy"),)


class ObligationProduct(Base):
    """Mapping: which products an obligation applies to."""

    __tablename__ = "obligation_products"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    obligation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("obligation_id", "product_id", name="uq_obligation_product"),
    )
