"""app tables: monitoring, knowledge base, obligations, tasks, alerts

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.create_table(
        "monitoring_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("regulator_key", sa.String(32), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("base_url", sa.Text, nullable=False),
        sa.Column("scraper_kind", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("cadence_hours", sa.Integer, nullable=False, server_default="6"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("regulator_key", "scraper_kind", name="uq_monitoring_source"),
    )

    op.create_table(
        "scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("monitoring_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("docs_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("docs_new", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_scan_runs_source_id", "scan_runs", ["source_id"])

    op.create_table(
        "company_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("mime", sa.String(128), nullable=True),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("org_id", "content_hash", name="uq_company_document_hash"),
    )
    op.execute(
        "CREATE INDEX ix_company_documents_embedding_hnsw "
        "ON company_documents USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "company_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True, unique=True),
        sa.Column(
            "entity_classes",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "topics", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "regulators", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "derived_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "obligations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "regulation_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("what_changed", sa.Text, nullable=True),
        sa.Column("gap_analysis", sa.Text, nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("org_id", "regulation_node_id", name="uq_obligation_per_regulation"),
    )
    op.create_index("ix_obligations_regulation_node_id", "obligations", ["regulation_node_id"])
    op.create_index("ix_obligations_status", "obligations", ["status"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "obligation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obligations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "deadline_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("owner", sa.Text, nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(16), nullable=False, server_default="todo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_tasks_obligation_id", "tasks", ["obligation_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column(
            "regulation_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "obligation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obligations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("tasks")
    op.drop_table("obligations")
    op.drop_table("company_profiles")
    op.execute("DROP INDEX IF EXISTS ix_company_documents_embedding_hnsw")
    op.drop_table("company_documents")
    op.drop_table("scan_runs")
    op.drop_table("monitoring_sources")
