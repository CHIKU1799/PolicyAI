from __future__ import annotations

import os
import ssl
from urllib.parse import quote, unquote

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return url


def _encode_userinfo(url: str) -> str:
    """Percent-encode the user:password so special characters don't break URL
    parsing — Supabase passwords frequently contain ``@``, which otherwise makes
    SQLAlchemy mis-read the host. Idempotent (decodes then re-encodes), so an
    already-encoded URL is left effectively unchanged."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    if "@" not in rest:
        return url
    userinfo, hostpart = rest.rsplit("@", 1)  # last @ separates creds from host
    if ":" not in userinfo:
        return url
    user, password = userinfo.split(":", 1)
    safe_user = quote(unquote(user), safe="")
    safe_pw = quote(unquote(password), safe="")
    return f"{scheme}://{safe_user}:{safe_pw}@{hostpart}"


def _normalize_async_url(url: str) -> str:
    """Force the asyncpg driver. Supabase's dashboard URI comes as
    ``postgresql://...`` (which SQLAlchemy routes to psycopg2); rewrite it so a
    pasted connection string just works."""
    if url.startswith("postgresql+"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


def make_engine(url: str | None = None, *, echo: bool = False) -> AsyncEngine:
    resolved = _normalize_async_url(_encode_userinfo(url or get_database_url()))
    connect_args: dict = {}
    # Supabase fronts Postgres with PgBouncer. In transaction-pooling mode the
    # asyncpg prepared-statement cache raises DuplicatePreparedStatementError on
    # reused connections. Disabling the cache makes the driver pooler-safe at a
    # negligible cost; harmless on a direct/session connection too.
    if "asyncpg" in resolved:
        connect_args["statement_cache_size"] = 0
        # Supabase requires TLS; asyncpg doesn't infer it from the URL. Encrypt the
        # connection but skip cert-chain verification (the client often lacks
        # Supabase's CA, and proxies can present a self-signed chain) — the
        # widely-used asyncpg + Supabase pattern. For strict prod verification,
        # set DB_SSL_VERIFY=true and ensure the Supabase CA is in the trust store.
        if "supabase" in resolved or "pooler" in resolved:
            ctx = ssl.create_default_context()
            if os.getenv("DB_SSL_VERIFY", "false").lower() != "true":
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ctx
    return create_async_engine(resolved, echo=echo, pool_pre_ping=True, connect_args=connect_args)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
