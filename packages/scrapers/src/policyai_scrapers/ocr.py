"""OCR for scanned regulator PDFs (NPCI, DGFT) that carry no text layer.

Pure-pip pipeline: pypdfium2 rasterizes pages (no poppler) and RapidOCR runs
detection + recognition with ONNX models bundled in its wheel (no downloads, no
system packages), so the slim Docker image works unchanged. The engine is a
lazy module-level singleton: nothing loads at import time, and the first call
pays the one-time model load (~1-2s) for the whole process.
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np

from policyai_scrapers.util import log

_engine: Any = None


def _get_engine() -> Any:
    """RapidOCR singleton, created on first use."""
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _engine = RapidOCR()
    return _engine


def pdf_ocr_text(pdf_bytes: bytes, max_pages: int = 12, dpi: int = 200) -> str:
    """OCR a PDF's pages and return the recognized text, pages joined in order.

    Pages are rasterized at ``dpi`` (200 is plenty for the typewriter-style
    scans regulators publish) and capped at ``max_pages``: circulars are short,
    and the cap bounds worst-case cost on the odd long annexure."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(io.BytesIO(pdf_bytes))
    try:
        n_pages = len(doc)
        if n_pages > max_pages:
            log.info("ocr: truncating %d-page pdf to first %d pages", n_pages, max_pages)
        engine = _get_engine()
        page_texts: list[str] = []
        for i in range(min(n_pages, max_pages)):
            page = doc[i]
            bitmap = page.render(scale=dpi / 72)
            try:
                image = np.asarray(bitmap.to_pil().convert("RGB"))
            finally:
                bitmap.close()
                page.close()
            result, _ = engine(image)
            # RapidOCR returns [box, text, score] per line, already sorted in
            # reading order (top-to-bottom, left-to-right within a band).
            lines = [text for _box, text, _score in (result or [])]
            if lines:
                page_texts.append("\n".join(lines))
        return "\n\n".join(page_texts).strip()
    finally:
        doc.close()
