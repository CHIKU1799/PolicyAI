"""multi-tenancy: organizations + memberships

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "memberships",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column(
            "org_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(32), nullable=False, server_default="member"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "org_id", name="uq_membership"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    # The default org owns all pre-existing data; create it so FKs and RLS resolve.
    op.execute(
        f"INSERT INTO organizations (id, name) "
        f"VALUES ('{DEFAULT_ORG_ID}', 'Demo Microfinance Co.') ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("organizations")
