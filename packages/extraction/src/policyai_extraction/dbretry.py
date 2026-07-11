"""Detecting transient DB connection drops worth retrying.

The Supabase session pooler occasionally closes an idle connection mid-operation
(asyncpg ConnectionDoesNotExistError / "connection was closed"). That is transient:
SQLAlchemy invalidates the dead connection and the next statement gets a fresh one,
so the right response is to roll back and retry the SAME unit of work rather than
drop it. Used by both the regulation ingest loop and the obligation mapping loop.
"""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

_TRANSIENT_MARKERS = (
    # DB / pooler connection drops
    "connectiondoesnotexist",
    "connection was closed",
    "connection is closed",
    "server closed the connection",
    "connection reset",
    "cannot perform operation",
    "operation in progress",
    "ssl connection has been closed",
    # Network / DNS blips during outbound LLM/embedding calls (a brief blackout
    # should retry, not permanently drop the regulation — the Anthropic SDK raises
    # APIConnectionError "Connection error."; getaddrinfo raises these gaierror msgs)
    "connection error",
    "nodename nor servname",
    "name or service not known",
    "temporary failure in name resolution",
    "timed out",
    "connection refused",
)

# Default number of attempts (1 initial + retries) for a retried unit of work.
MAX_ATTEMPTS = 3


def is_transient(exc: Exception) -> bool:
    """True for connection-level blips worth retrying (vs. a real error)."""
    if isinstance(exc, (InterfaceError, OperationalError)):
        return True
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)
