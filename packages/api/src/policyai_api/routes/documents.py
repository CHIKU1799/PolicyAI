"""Knowledge-base document processing: extract text, embed, store the row.

The browser uploads the file straight to Supabase Storage (signed URL), then
calls this endpoint with the storage path. We pull the bytes, extract text, embed,
and persist a CompanyDocument. Scanned PDFs with no text layer are flagged
``needs_ocr`` instead of being embedded empty.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from policyai_extraction.embeddings import embed_text
from policyai_graph.models_app import CompanyDocument, DocumentStatus
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.auth import Principal, effective_org, resolve_principal
from policyai_api.deps import download_from_storage, get_session
from policyai_api.ratelimit import rate_limited
from policyai_api.textextract import extract_text

router = APIRouter(prefix="/documents", tags=["documents"])

# Only formats textextract can actually handle; everything else is refused
# instead of being stored as an opaque blob in the org's knowledge base.
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _max_upload_bytes() -> int:
    try:
        mb = max(1, int(os.getenv("UPLOAD_MAX_MB", "")))
    except ValueError:
        mb = 25
    return mb * 1024 * 1024


def _validate_storage_path(storage_path: str, org_id: UUID) -> None:
    """The path must be a clean, org-prefixed object key: no traversal, no
    absolute paths, and it must live under the caller's own org folder so one
    tenant can never point the worker at another tenant's uploaded file."""
    path = storage_path.strip()
    if (
        not path
        or path != storage_path
        or "\\" in path
        or path.startswith("/")
        or ".." in path.split("/")
        or posixpath.normpath(path) != path
    ):
        raise HTTPException(status_code=422, detail="invalid storage path")
    prefix, _, rest = path.partition("/")
    if prefix != str(org_id) or not rest:
        raise HTTPException(
            status_code=403,
            detail="storage path must be under your organization's folder (<org_id>/...)",
        )


class ProcessRequest(BaseModel):
    storage_path: str
    filename: str
    mime: str | None = None
    org_id: UUID | None = None  # honored only for platform admins


class ProcessResponse(BaseModel):
    id: UUID
    status: str
    chars: int


@router.post(
    "/process",
    response_model=ProcessResponse,
    dependencies=[Depends(rate_limited("documents", require_auth=True))],
)
async def process_document(
    req: ProcessRequest,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(resolve_principal),
) -> ProcessResponse:
    org_id = effective_org(principal, req.org_id)
    ext = posixpath.splitext(req.filename.strip().lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported file type {ext or '(none)'}; "
            f"allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    _validate_storage_path(req.storage_path, org_id)
    try:
        content = await download_from_storage(req.storage_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"storage fetch failed: {exc}") from exc
    if len(content) > _max_upload_bytes():
        raise HTTPException(
            status_code=413,
            detail=f"file too large ({len(content) // (1024 * 1024)} MB); "
            f"max {_max_upload_bytes() // (1024 * 1024)} MB",
        )

    text = extract_text(content, filename=req.filename, mime=req.mime)
    content_hash = hashlib.sha256(content).hexdigest()

    existing = (
        await session.execute(
            select(CompanyDocument).where(
                CompanyDocument.org_id == org_id,
                CompanyDocument.content_hash == content_hash,
            )
        )
    ).scalar_one_or_none()
    doc = existing or CompanyDocument(org_id=org_id)
    doc.storage_path = req.storage_path
    doc.filename = req.filename
    doc.mime = req.mime
    doc.content_hash = content_hash
    doc.raw_text = text

    if len(text) < 50:
        doc.status = DocumentStatus.NEEDS_OCR.value
    else:
        try:
            doc.embedding = await embed_text(text[:8000])
            doc.status = DocumentStatus.PROCESSED.value
        except Exception as exc:  # noqa: BLE001
            doc.status = DocumentStatus.FAILED.value
            print(f"[documents] embedding failed: {exc}")

    if existing is None:
        session.add(doc)
    await session.commit()
    await session.refresh(doc)

    # Self-serve pipeline: once a firm's document is in, derive its profile
    # (when missing) and run a bounded obligation-mapping pass in the
    # background, so the dashboard fills in without a manual trigger.
    if doc.status == DocumentStatus.PROCESSED.value:
        from policyai_extraction.profile_derive import ensure_profile_and_map

        background.add_task(ensure_profile_and_map, org_id)

    return ProcessResponse(id=doc.id, status=doc.status, chars=len(text))
