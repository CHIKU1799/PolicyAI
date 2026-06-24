"""GRC core: policies, controls, products, gaps, audit, obligation mappings

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _org():
    return sa.Column("org_id", UUID, nullable=True)


def _created():
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "policies",
        sa.Column("id", UUID, primary_key=True),
        _org(),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("owner", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        _created(),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "policy_id", UUID, sa.ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("change_note", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Text, nullable=True),
        sa.Column("approved_by", sa.Text, nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        _created(),
        sa.UniqueConstraint("policy_id", "version_no", name="uq_policy_version"),
    )

    op.create_table(
        "controls",
        sa.Column("id", UUID, primary_key=True),
        _org(),
        sa.Column("ref_code", sa.String(64), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("control_type", sa.String(16), nullable=False, server_default="preventive"),
        sa.Column("frequency", sa.String(32), nullable=True),
        sa.Column("owner", sa.Text, nullable=True),
        sa.Column("effectiveness", sa.String(16), nullable=False, server_default="untested"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        _created(),
    )

    op.create_table(
        "control_tests",
        sa.Column("id", UUID, primary_key=True),
        _org(),
        sa.Column(
            "control_id", UUID, sa.ForeignKey("controls.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("scheduled_for", sa.Date, nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_by", sa.Text, nullable=True),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("evidence", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        _created(),
    )
    op.create_index("ix_control_tests_control_id", "control_tests", ["control_id"])

    op.create_table(
        "products",
        sa.Column("id", UUID, primary_key=True),
        _org(),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("entity_class", sa.String(64), nullable=True),
        _created(),
    )

    op.create_table(
        "gaps",
        sa.Column("id", UUID, primary_key=True),
        _org(),
        sa.Column(
            "obligation_id",
            UUID,
            sa.ForeignKey("obligations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("remediation_plan", sa.Text, nullable=True),
        sa.Column("owner", sa.Text, nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        _created(),
    )
    op.create_index("ix_gaps_obligation_id", "gaps", ["obligation_id"])
    op.create_index("ix_gaps_status", "gaps", ["status"])

    op.create_table(
        "audit_events",
        sa.Column("id", UUID, primary_key=True),
        _org(),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.Text, nullable=True),
        sa.Column(
            "detail", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        _created(),
    )
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])

    for name, col, target in [
        ("obligation_controls", "control_id", "controls"),
        ("obligation_policies", "policy_id", "policies"),
        ("obligation_products", "product_id", "products"),
    ]:
        op.create_table(
            name,
            sa.Column("id", UUID, primary_key=True),
            _org(),
            sa.Column(
                "obligation_id",
                UUID,
                sa.ForeignKey("obligations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(col, UUID, sa.ForeignKey(f"{target}.id", ondelete="CASCADE"), nullable=False),
            _created(),
            sa.UniqueConstraint("obligation_id", col, name=f"uq_{name}"),
        )


def downgrade() -> None:
    for t in [
        "obligation_products",
        "obligation_policies",
        "obligation_controls",
        "audit_events",
        "gaps",
        "products",
        "control_tests",
        "controls",
        "policy_versions",
        "policies",
    ]:
        op.drop_table(t)
