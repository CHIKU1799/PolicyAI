"""Mapping confidence + relevance rationale on obligations.

Records how confident the mapping engine is that a regulation applies to the org,
and the one-line reason it gave — the audit trail behind every obligation and the
signal that lets the UI surface low-confidence mappings for human review.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-28

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("obligations", sa.Column("mapping_confidence", sa.Float, nullable=True))
    op.add_column("obligations", sa.Column("relevance_rationale", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("obligations", "relevance_rationale")
    op.drop_column("obligations", "mapping_confidence")
