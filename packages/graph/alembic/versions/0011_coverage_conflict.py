"""Coverage classification + cited evidence on gaps (coverage + conflict engine).

Turns a gap from "something's missing" into a defensible finding: how the firm's
policy covers the requirement (covered/partial/missing/conflicting) and the exact
policy passage that proves it. ``conflicting`` — the policy actively contradicts a
regulation — is the highest penalty risk and now first-class.

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gaps", sa.Column("coverage_status", sa.String(16), nullable=True))
    op.add_column("gaps", sa.Column("evidence_quote", sa.Text(), nullable=True))
    op.add_column(
        "gaps",
        sa.Column(
            "evidence_doc_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Fast filter for the "policy conflicts" insight and coverage rollups.
    op.create_index(
        "ix_gaps_coverage_status",
        "gaps",
        ["org_id", "coverage_status"],
        postgresql_where=sa.text("coverage_status IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_gaps_coverage_status", table_name="gaps")
    op.drop_column("gaps", "evidence_doc_id")
    op.drop_column("gaps", "evidence_quote")
    op.drop_column("gaps", "coverage_status")
