"""Shared dependencies: DB session, LLM client, Supabase storage, auth guard."""

from __future__ import annotations

import functools
import os
from collections.abc import AsyncIterator

import httpx
from fastapi import Header, HTTPException
from policyai_extraction.llm import LLMClient
from policyai_graph.db import make_engine, make_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@functools.lru_cache(maxsize=1)
def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    # Lazy so importing the app (e.g. in tests) doesn't require DATABASE_URL.
    return make_sessionmaker(make_engine())


@functools.lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    return LLMClient()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _get_sessionmaker()() as session:
        yield session


async def download_from_storage(storage_path: str) -> bytes:
    """Fetch an uploaded file from Supabase Storage using the service-role key."""
    base = os.environ["SUPABASE_URL"].rstrip("/")
    bucket = os.getenv("SUPABASE_KB_BUCKET", "company-documents")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    url = f"{base}/storage/v1/object/{bucket}/{storage_path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        return resp.content


def require_internal_secret(x_internal_secret: str = Header(default="")) -> None:
    """Guard internal endpoints (pg_net trigger / manual re-run) with a shared secret."""
    expected = os.getenv("INTERNAL_API_SECRET", "")
    if not expected or x_internal_secret != expected:
        raise HTTPException(status_code=401, detail="invalid internal secret")
