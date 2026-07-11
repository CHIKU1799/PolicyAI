"""Requirement-level gaps.

Adds ``gaps.requirement_id`` so a gap can be scoped to a single atomic requirement
(null = the obligation-level summary gap). This turns "gap analysis" from one text
blob per obligation into a concrete, per-requirement coverage map.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "gaps",
        sa.Column(
            "requirement_id",
            UUID,
            sa.ForeignKey("requirements.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_gaps_requirement", "gaps", ["requirement_id"])


def downgrade() -> None:
    op.drop_index("ix_gaps_requirement", table_name="gaps")
    op.drop_column("gaps", "requirement_id")
