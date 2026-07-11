"""Widen citation columns from varchar(128) to Text.

The mapping model generates ``regulatory_citation`` values that chain multiple
references (e.g. a circular read with its parent master direction), which routinely
exceed 128 characters and hard-failed the whole obligation write with
StringDataRightTruncationError. Citations are legitimately unbounded, so store them
as Text. ``requirements.citation`` holds the same kind of data and is widened too.

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "obligations",
        "regulatory_citation",
        type_=sa.Text(),
        existing_type=sa.String(128),
        existing_nullable=True,
    )
    op.alter_column(
        "requirements",
        "citation",
        type_=sa.Text(),
        existing_type=sa.String(128),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Truncating back to 128 could lose data; cast explicitly so downgrade is total.
    op.alter_column(
        "obligations",
        "regulatory_citation",
        type_=sa.String(128),
        existing_type=sa.Text(),
        existing_nullable=True,
        postgresql_using="left(regulatory_citation, 128)",
    )
    op.alter_column(
        "requirements",
        "citation",
        type_=sa.String(128),
        existing_type=sa.Text(),
        existing_nullable=True,
        postgresql_using="left(citation, 128)",
    )
