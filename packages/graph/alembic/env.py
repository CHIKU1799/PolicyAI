from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

# Import side effect: register the application tables on ``Base.metadata`` so
# Alembic autogenerate and ``target_metadata`` see them alongside the graph.
import policyai_graph.models_app  # noqa: E402,F401
from alembic import context
from policyai_graph.models import Base
from sqlalchemy.engine import Connection

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Use the project engine factory so URL normalization (asyncpg driver,
    # percent-encoded credentials) and Supabase SSL handling apply here too.
    from policyai_graph.db import make_engine

    connectable = make_engine()
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
