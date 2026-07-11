"""Atomic requirements + richer obligation metadata.

Adds a ``requirements`` table holding the discrete, actionable requirements
extracted from each regulation (with type, frequency, citation, evidence and
penalty), and enriches ``obligations`` with concrete compliance metadata
(obligation_type, frequency, regulatory_citation, penalty_summary,
evidence_required). Document type / reference number / penalties for a regulation
live in the node's JSONB properties, so they need no column.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "requirements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("org_id", UUID, nullable=True),
        sa.Column(
            "regulation_node_id",
            UUID,
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("requirement_type", sa.String(32), nullable=False, server_default="operational"),
        sa.Column("applies_to", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("frequency", sa.String(32), nullable=True),
        sa.Column("citation", sa.String(128), nullable=True),
        sa.Column("evidence_expected", sa.Text, nullable=True),
        sa.Column("penalty", sa.Text, nullable=True),
        sa.Column("seq", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("regulation_node_id", "seq", name="uq_requirement_seq"),
    )
    op.create_index("ix_requirements_regulation", "requirements", ["regulation_node_id"])

    op.add_column(
        "obligations",
        sa.Column("obligation_type", sa.String(32), nullable=False, server_default="operational"),
    )
    op.add_column("obligations", sa.Column("frequency", sa.String(32), nullable=True))
    op.add_column("obligations", sa.Column("regulatory_citation", sa.String(128), nullable=True))
    op.add_column("obligations", sa.Column("penalty_summary", sa.Text, nullable=True))
    op.add_column("obligations", sa.Column("evidence_required", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("obligations", "evidence_required")
    op.drop_column("obligations", "penalty_summary")
    op.drop_column("obligations", "regulatory_citation")
    op.drop_column("obligations", "frequency")
    op.drop_column("obligations", "obligation_type")
    op.drop_index("ix_requirements_regulation", table_name="requirements")
    op.drop_table("requirements")
