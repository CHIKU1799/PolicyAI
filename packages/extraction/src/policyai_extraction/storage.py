"""Pluggable object storage — Supabase Storage (default) or Cloudflare R2.

R2 is S3-compatible with zero egress fees, which makes it the ideal "document
lake" for the raw circulars, uploaded policy docs, and control-test evidence that
the platform re-reads constantly. Switch with one env var; the API is identical.

  STORAGE_BACKEND=supabase   (default — uses SUPABASE_URL + service-role key)
  STORAGE_BACKEND=r2         (set R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
                              R2_BUCKET; needs `uv add aioboto3`)

Shared by the worker (downloads) and the scrapers (archiving raw documents), so a
single switch moves the whole document lake to R2.
"""

from __future__ import annotations

import os

import httpx

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "supabase").lower()
DEFAULT_BUCKET = os.getenv("SUPABASE_KB_BUCKET", "company-documents")
_TIMEOUT = httpx.Timeout(60.0)


def archive_enabled() -> bool:
    """Whether the crawler should archive raw documents to the lake. On by default
    for R2 (that's the point); opt-in for Supabase via ARCHIVE_RAW=true."""
    return STORAGE_BACKEND == "r2" or os.getenv("ARCHIVE_RAW", "false").lower() == "true"


async def download(path: str, *, bucket: str | None = None) -> bytes:
    bucket = bucket or DEFAULT_BUCKET
    if STORAGE_BACKEND == "r2":
        return await _r2_download(path, bucket)
    return await _supabase_download(path, bucket)


async def upload(
    path: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> str:
    """Store bytes and return the storage path (key)."""
    bucket = bucket or DEFAULT_BUCKET
    if STORAGE_BACKEND == "r2":
        await _r2_upload(path, data, content_type, bucket)
    else:
        await _supabase_upload(path, data, content_type, bucket)
    return path


# --- Supabase Storage (REST, service-role) --------------------------------
def _supabase_url(path: str, bucket: str) -> str:
    base = os.environ["SUPABASE_URL"].rstrip("/")
    return f"{base}/storage/v1/object/{bucket}/{path.lstrip('/')}"


async def _supabase_download(path: str, bucket: str) -> bytes:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.get(_supabase_url(path, bucket), headers={"Authorization": f"Bearer {key}"})
        r.raise_for_status()
        return r.content


async def _supabase_upload(path: str, data: bytes, content_type: str, bucket: str) -> None:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(
            _supabase_url(path, bucket),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
            content=data,
        )
        r.raise_for_status()


# --- Cloudflare R2 (S3-compatible) ----------------------------------------
def _r2_client():
    try:
        import aioboto3
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError("STORAGE_BACKEND=r2 needs aioboto3 — run `uv add aioboto3`.") from exc
    session = aioboto3.Session()
    return session.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],  # https://<account>.r2.cloudflarestorage.com
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _r2_bucket(bucket: str) -> str:
    return os.getenv("R2_BUCKET", bucket)


async def _r2_download(path: str, bucket: str) -> bytes:
    async with _r2_client() as s3:
        obj = await s3.get_object(Bucket=_r2_bucket(bucket), Key=path.lstrip("/"))
        return await obj["Body"].read()


async def _r2_upload(path: str, data: bytes, content_type: str, bucket: str) -> None:
    async with _r2_client() as s3:
        await s3.put_object(
            Bucket=_r2_bucket(bucket), Key=path.lstrip("/"), Body=data, ContentType=content_type
        )
