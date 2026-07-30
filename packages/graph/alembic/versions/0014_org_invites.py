"""org invites: team invitations per org

One row per invitation an org admin sends. If the invitee already has an auth
account the worker adds the membership immediately and stamps accepted_at;
otherwise the Supabase signup trigger consumes the pending invite when the
invitee registers (see supabase/migrations/0014_org_invites.sql).

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "org_invites",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "org_id",
            UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_org_invites_org_id", "org_invites", ["org_id"])
    # The signup trigger looks pending invites up by lowercased email.
    op.create_index("ix_org_invites_email", "org_invites", ["email"])


def downgrade() -> None:
    op.drop_index("ix_org_invites_email", table_name="org_invites")
    op.drop_index("ix_org_invites_org_id", table_name="org_invites")
    op.drop_table("org_invites")
