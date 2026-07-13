"""demo / sales contact requests from the marketing site

One row per submitted contact form (Book a demo / Talk to sales). Written by the
worker's public /contact endpoint; read by operators only.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "demo_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("intent", sa.String(16), nullable=False, server_default="demo"),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("company", sa.Text, nullable=False),
        sa.Column("segment", sa.String(32), nullable=True),
        sa.Column("phone", sa.Text, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="new"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_demo_requests_created_at", "demo_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_demo_requests_created_at", table_name="demo_requests")
    op.drop_table("demo_requests")
