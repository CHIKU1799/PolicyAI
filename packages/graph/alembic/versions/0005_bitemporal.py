"""Bitemporal KG: validity/invalidation on nodes, edges, obligations, gaps,
controls + a full-text search_vector for hybrid retrieval.

Adds two time axes so PolicyAI can answer "what was in force as of date X" and
"what got invalidated when": valid-time (effective_from/effective_to) and
transaction-time (recorded_at/invalidated_at), plus supersession pointers and an
is_current flag. Also adds a generated tsvector + GIN index on raw_documents to
back keyword search alongside pgvector.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def _temporal_cols(self_table: str) -> list[sa.Column]:
    """The shared validity/invalidation columns added to obligations/gaps/controls."""
    return [
        sa.Column("effective_date", sa.Date, nullable=True),
        sa.Column("valid_to", sa.Date, nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "superseded_by_id",
            UUID,
            sa.ForeignKey(f"{self_table}.id", ondelete="SET NULL"),
            nullable=True,
        ),
    ]


def upgrade() -> None:
    # --- nodes: bitemporal axes -------------------------------------------
    op.add_column("nodes", sa.Column("effective_from", sa.Date, nullable=True))
    op.add_column("nodes", sa.Column("effective_to", sa.Date, nullable=True))
    op.add_column(
        "nodes",
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column("nodes", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "nodes",
        sa.Column(
            "superseded_by_node_id",
            UUID,
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "nodes",
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_nodes_is_current", "nodes", ["node_type", "is_current"])
    op.create_index("ix_nodes_effective", "nodes", ["effective_from", "effective_to"])

    # Backfill: regulations take effect on their published date; record-time = creation.
    op.execute(
        "UPDATE nodes SET effective_from = (properties->>'published_date')::date "
        "WHERE node_type = 'regulation' AND properties->>'published_date' IS NOT NULL "
        "AND effective_from IS NULL"
    )
    op.execute("UPDATE nodes SET recorded_at = created_at")

    # --- edges: relationship validity -------------------------------------
    op.add_column("edges", sa.Column("valid_from", sa.Date, nullable=True))
    op.add_column("edges", sa.Column("valid_to", sa.Date, nullable=True))
    op.add_column("edges", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))

    # --- obligations / gaps / controls: validity + supersession -----------
    for col in _temporal_cols("obligations"):
        op.add_column("obligations", col)
    for col in _temporal_cols("gaps"):
        op.add_column("gaps", col)
    for col in _temporal_cols("controls"):
        op.add_column("controls", col)
    op.execute(
        "UPDATE obligations SET effective_date = created_at::date WHERE effective_date IS NULL"
    )

    # --- raw_documents: full-text search_vector for hybrid retrieval -------
    op.add_column(
        "raw_documents",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(raw_text, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_raw_documents_search_vector",
        "raw_documents",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_raw_documents_search_vector", table_name="raw_documents")
    op.drop_column("raw_documents", "search_vector")

    for table in ("controls", "gaps", "obligations"):
        op.drop_column(table, "superseded_by_id")
        op.drop_column(table, "invalidated_at")
        op.drop_column(table, "valid_to")
        op.drop_column(table, "effective_date")

    op.drop_column("edges", "invalidated_at")
    op.drop_column("edges", "valid_to")
    op.drop_column("edges", "valid_from")

    op.drop_index("ix_nodes_effective", table_name="nodes")
    op.drop_index("ix_nodes_is_current", table_name="nodes")
    op.drop_column("nodes", "is_current")
    op.drop_column("nodes", "superseded_by_node_id")
    op.drop_column("nodes", "invalidated_at")
    op.drop_column("nodes", "recorded_at")
    op.drop_column("nodes", "effective_to")
    op.drop_column("nodes", "effective_from")
