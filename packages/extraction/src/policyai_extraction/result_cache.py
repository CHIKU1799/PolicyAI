"""Persistent result cache for deterministic LLM extraction calls.

Backfills re-run the same (document, prompt, schema, model) extractions when a
run is killed mid-way; every replayed call is money spent twice. This module
stores each validated extraction result in the ``llm_cache`` table keyed by a
sha256 of the full request, so a rerun replays past work for free.

Deliberately failure-tolerant: a cache read or write that fails for any reason
(no DATABASE_URL, migration not applied, transient outage) logs and continues —
the LLM call must never break because the cache did.

Disable with ``LLM_RESULT_CACHE=0``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from policyai_graph.models_app import LlmCache
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Lazily-built module-level session factory (its own engine, independent of the
# pipeline's transaction, so cache traffic never entangles caller sessions).
# Tests may inject a fake factory here.
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        from policyai_graph.db import make_engine, make_sessionmaker

        _sessionmaker = make_sessionmaker(make_engine())
    return _sessionmaker


def make_key(payload: dict[str, Any]) -> str:
    """sha256 hex of the canonical JSON of ``payload`` — stable across dict
    insertion order so semantically identical requests share a key."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def get(key: str) -> dict[str, Any] | None:
    """Cached response payload for ``key``, or None on miss or any failure."""
    try:
        async with _get_sessionmaker()() as session:
            return (
                await session.execute(select(LlmCache.response).where(LlmCache.cache_key == key))
            ).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001 - cache failure must never break the call
        print(f"[result-cache] read failed ({key[:12]}…): {exc}")
        return None


async def put(key: str, model: str | None, purpose: str | None, payload: dict[str, Any]) -> None:
    """Store a validated result. Idempotent (first write wins); never raises."""
    try:
        async with _get_sessionmaker()() as session:
            await session.execute(
                pg_insert(LlmCache)
                .values(cache_key=key, model=model, purpose=purpose, response=payload)
                .on_conflict_do_nothing(index_elements=["cache_key"])
            )
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - cache failure must never break the call
        print(f"[result-cache] write failed ({key[:12]}…): {exc}")
