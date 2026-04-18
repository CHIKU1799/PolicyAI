from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio
async def test_pgvector_extension_installed(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        assert result.scalar_one() == "vector"


@pytest.mark.asyncio
async def test_all_tables_exist(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
        tables = {row[0] for row in result}
    assert {"nodes", "edges", "raw_documents"}.issubset(tables)


@pytest.mark.asyncio
async def test_btree_index_on_node_type(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' AND indexname = 'ix_nodes_node_type'"
            )
        )
        indexdef = result.scalar_one()
    assert "btree" in indexdef.lower()
    assert "node_type" in indexdef


@pytest.mark.asyncio
async def test_gin_index_on_node_properties(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' AND indexname = 'ix_nodes_properties_gin'"
            )
        )
        indexdef = result.scalar_one()
    assert "gin" in indexdef.lower()
    assert "properties" in indexdef


@pytest.mark.asyncio
async def test_hnsw_index_on_raw_document_embedding(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "AND indexname = 'ix_raw_documents_embedding_hnsw'"
            )
        )
        indexdef = result.scalar_one()
    assert "hnsw" in indexdef.lower()
    assert "embedding" in indexdef
    assert "vector_cosine_ops" in indexdef


@pytest.mark.asyncio
async def test_edge_unique_triple_constraint(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'uq_edge_triple'"
            )
        )
        assert result.scalar_one() == "uq_edge_triple"
