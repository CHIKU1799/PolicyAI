"""llm cache: persistent result cache for deterministic LLM extraction calls

One row per unique extraction request, keyed by a sha256 of the full request
(provider, model, system, messages, schema, max_tokens, purpose). Lets a
killed-and-rerun backfill replay already-paid-for results instead of calling
the model again.

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "llm_cache",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cache_key", sa.Text, nullable=False, unique=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("purpose", sa.Text, nullable=True),
        sa.Column("response", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("llm_cache")
