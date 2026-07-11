"""platform admins + org slug/created_by (multi-tenancy)

Adds the platform-level super-admin table and two org quality columns. The
per-firm provisioning + cross-org read logic lives in the companion RLS file
supabase/migrations/0012_multitenant_provisioning.sql (run in Supabase after this).

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("organizations", sa.Column("slug", sa.Text, nullable=True))
    op.add_column("organizations", sa.Column("created_by", UUID, nullable=True))
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "platform_admins",
        sa.Column("user_id", UUID, primary_key=True),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("platform_admins")
    op.drop_constraint("uq_organizations_slug", "organizations", type_="unique")
    op.drop_column("organizations", "created_by")
    op.drop_column("organizations", "slug")
