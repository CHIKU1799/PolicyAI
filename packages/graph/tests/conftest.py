from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from policyai_graph.db import make_engine, make_sessionmaker

GRAPH_PKG_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL not set — integration tests require a running "
            "Postgres with pgvector. Set it to e.g. "
            "postgresql+asyncpg://policyai:policyai@localhost:5432/policyai_test"
        )
    return url


@pytest_asyncio.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    """Reset the test DB and apply alembic migrations once per test session."""
    reset_engine = make_engine(database_url)
    async with reset_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await reset_engine.dispose()

    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=GRAPH_PKG_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    eng = make_engine(database_url)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Fresh session per test; truncates tables on teardown to keep tests isolated."""
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE TABLE raw_documents, edges, nodes RESTART IDENTITY CASCADE")
        )
