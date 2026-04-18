"""initial schema: nodes, edges, raw_documents + indexes

Revision ID: 0001
Revises:
Create Date: 2026-04-18

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("node_type", sa.String(32), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_nodes_node_type", "nodes", ["node_type"])
    op.execute("CREATE INDEX ix_nodes_properties_gin ON nodes USING gin (properties)")

    op.create_table(
        "edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_type", sa.String(32), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_id", "target_id", "edge_type", name="uq_edge_triple"
        ),
    )
    op.create_index("ix_edges_edge_type", "edges", ["edge_type"])
    op.create_index("ix_edges_source_id", "edges", ["source_id"])
    op.create_index("ix_edges_target_id", "edges", ["target_id"])

    op.create_table(
        "raw_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("published_date", sa.Date, nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "regulation_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("source", "source_id", name="uq_raw_document_source_id"),
    )
    op.execute(
        "CREATE INDEX ix_raw_documents_embedding_hnsw "
        "ON raw_documents USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("raw_documents")
    op.drop_table("edges")
    op.drop_table("nodes")
    op.execute("DROP EXTENSION IF EXISTS vector")
