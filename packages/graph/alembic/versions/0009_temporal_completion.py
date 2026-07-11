"""Complete the bitemporal model.

Three gaps in the 0005 temporal work:

1. ``requirements`` had no time axis, so when a regulation was superseded its
   requirements were orphaned — a point-in-time query would still return them and
   any requirement-scoped gap pointed at a "live" requirement of a dead document.
   Adds effective_date / valid_to / invalidated_at / superseded_by_id (+ a backfill)
   and supersede_node() now closes them.

2. The app tables had only ``created_at`` (row-insert), conflating it with the
   transaction-time axis. Adds an explicit ``recorded_at`` (when PolicyAI learned
   the fact) to obligations / gaps / controls / requirements, so "what did we
   believe on date X" is answerable independently of "what was in force on date X".

3. Supersession chains were walked without index support. Adds indexes on every
   ``superseded_by*`` pointer plus a composite valid-time index on obligations for
   point-in-time ("as of") filtering.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _recorded_at() -> sa.Column:
    return sa.Column(
        "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def upgrade() -> None:
    # --- requirements: full valid-time + transaction-time axis ------------
    op.add_column("requirements", sa.Column("effective_date", sa.Date, nullable=True))
    op.add_column("requirements", sa.Column("valid_to", sa.Date, nullable=True))
    op.add_column(
        "requirements", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "requirements",
        sa.Column(
            "superseded_by_id",
            UUID,
            sa.ForeignKey("requirements.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("requirements", _recorded_at())
    op.execute(
        "UPDATE requirements SET effective_date = created_at::date WHERE effective_date IS NULL"
    )
    op.execute("UPDATE requirements SET recorded_at = created_at")

    # --- transaction-time start on the remaining app tables ---------------
    for table in ("obligations", "gaps", "controls"):
        op.add_column(table, _recorded_at())
        op.execute(f"UPDATE {table} SET recorded_at = created_at")

    # --- supersession-chain + point-in-time indexes -----------------------
    op.create_index("ix_nodes_superseded", "nodes", ["superseded_by_node_id"])
    op.create_index("ix_obligations_superseded", "obligations", ["superseded_by_id"])
    op.create_index("ix_gaps_superseded", "gaps", ["superseded_by_id"])
    op.create_index("ix_controls_superseded", "controls", ["superseded_by_id"])
    op.create_index("ix_requirements_superseded", "requirements", ["superseded_by_id"])
    op.create_index("ix_requirements_valid", "requirements", ["effective_date", "valid_to"])
    op.create_index("ix_obligations_valid", "obligations", ["effective_date", "valid_to"])


def downgrade() -> None:
    op.drop_index("ix_obligations_valid", table_name="obligations")
    op.drop_index("ix_requirements_valid", table_name="requirements")
    op.drop_index("ix_requirements_superseded", table_name="requirements")
    op.drop_index("ix_controls_superseded", table_name="controls")
    op.drop_index("ix_gaps_superseded", table_name="gaps")
    op.drop_index("ix_obligations_superseded", table_name="obligations")
    op.drop_index("ix_nodes_superseded", table_name="nodes")

    for table in ("controls", "gaps", "obligations"):
        op.drop_column(table, "recorded_at")

    op.drop_column("requirements", "recorded_at")
    op.drop_column("requirements", "superseded_by_id")
    op.drop_column("requirements", "invalidated_at")
    op.drop_column("requirements", "valid_to")
    op.drop_column("requirements", "effective_date")
