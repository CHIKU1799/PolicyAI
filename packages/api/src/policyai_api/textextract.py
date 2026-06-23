"""Extract plain text from uploaded company documents (PDF / DOCX / text).

Scanned PDFs have no text layer — when extraction yields almost nothing we return
empty so the caller can flag the document ``needs_ocr`` rather than embedding an
empty string (which would poison similarity search)."""

from __future__ import annotations

import io


def extract_text(content: bytes, *, filename: str, mime: str | None) -> str:
    name = filename.lower()
    if name.endswith(".pdf") or (mime and "pdf" in mime):
        return _from_pdf(content)
    if name.endswith(".docx") or (mime and "word" in mime):
        return _from_docx(content)
    # Plain text / markdown / anything else decodable.
    try:
        return content.decode("utf-8", errors="ignore").strip()
    except Exception:  # noqa: BLE001
        return ""


def _from_pdf(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(parts).strip()


def _from_docx(content: bytes) -> str:
    from docx import Document

    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs).strip()
