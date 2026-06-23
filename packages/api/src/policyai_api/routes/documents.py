"""Knowledge-base document processing: extract text, embed, store the row.

The browser uploads the file straight to Supabase Storage (signed URL), then
calls this endpoint with the storage path. We pull the bytes, extract text, embed,
and persist a CompanyDocument. Scanned PDFs with no text layer are flagged
``needs_ocr`` instead of being embedded empty.
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from policyai_extraction.embeddings import embed_text
from policyai_graph.models_app import DEFAULT_ORG_ID, CompanyDocument, DocumentStatus
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from policyai_api.deps import download_from_storage, get_session
from policyai_api.textextract import extract_text

router = APIRouter(prefix="/documents", tags=["documents"])


class ProcessRequest(BaseModel):
    storage_path: str
    filename: str
    mime: str | None = None
    org_id: UUID = DEFAULT_ORG_ID


class ProcessResponse(BaseModel):
    id: UUID
    status: str
    chars: int


@router.post("/process", response_model=ProcessResponse)
async def process_document(
    req: ProcessRequest, session: AsyncSession = Depends(get_session)
) -> ProcessResponse:
    try:
        content = await download_from_storage(req.storage_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"storage fetch failed: {exc}") from exc

    text = extract_text(content, filename=req.filename, mime=req.mime)
    content_hash = hashlib.sha256(content).hexdigest()

    existing = (
        await session.execute(
            select(CompanyDocument).where(
                CompanyDocument.org_id == req.org_id,
                CompanyDocument.content_hash == content_hash,
            )
        )
    ).scalar_one_or_none()
    doc = existing or CompanyDocument(org_id=req.org_id)
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
    return ProcessResponse(id=doc.id, status=doc.status, chars=len(text))
