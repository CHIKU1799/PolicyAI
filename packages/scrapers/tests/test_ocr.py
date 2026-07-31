"""Tests for the scanned-PDF OCR path (``ocr.py``) and its wiring into
``browser_base.pdf_bytes_to_text``.

Fixtures are generated in-test: text rendered onto a PIL image and saved as a
PDF gives a faithful stand-in for the image-only scans NPCI/DGFT publish, with
no binary fixtures checked in. RapidOCR's models ship inside its wheel, so the
engine normally loads offline; if it still cannot initialise (e.g. a stripped
install), the OCR-engine tests skip rather than fail.
"""

from __future__ import annotations

import io

import pytest
from policyai_scrapers.browser_base import OCR_FALLBACK_CHARS, pdf_bytes_to_text


def _scanned_pdf(*page_lines: tuple[str, ...]) -> bytes:
    """A PDF whose pages are pure images (no text layer), one per tuple of lines."""
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.load_default(size=40)
    pages = []
    for lines in page_lines:
        img = Image.new("RGB", (1200, 120 + 100 * len(lines)), "white")
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            draw.text((60, 60 + 100 * i), line, fill="black", font=font)
        pages.append(img)
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()


def _require_engine() -> None:
    pytest.importorskip("rapidocr_onnxruntime")
    from policyai_scrapers.ocr import _get_engine

    try:
        _get_engine()
    except Exception as exc:  # noqa: BLE001 - models missing and not downloadable
        pytest.skip(f"rapidocr engine unavailable: {exc}")


def _squash(text: str) -> str:
    """OCR sometimes drops inter-word spaces; compare space-insensitively."""
    return "".join(text.lower().split())


def test_pdf_ocr_text_reads_scanned_pdf():
    _require_engine()
    from policyai_scrapers.ocr import pdf_ocr_text

    pdf = _scanned_pdf(
        ("Reserve Bank of India", "Circular No. 42 of 2026", "All member banks shall comply.")
    )
    text = pdf_ocr_text(pdf)
    assert "circularno.42of2026" in _squash(text)
    assert "memberbanks" in _squash(text)


def test_pdf_ocr_text_caps_pages():
    _require_engine()
    from policyai_scrapers.ocr import pdf_ocr_text

    pdf = _scanned_pdf(("FIRST PAGE MARKER ALPHA",), ("SECOND PAGE MARKER BRAVO",))
    text = pdf_ocr_text(pdf, max_pages=1)
    assert "alpha" in _squash(text)
    assert "bravo" not in _squash(text)


def test_pdf_bytes_to_text_falls_back_to_ocr(monkeypatch):
    """A PDF whose text layer is under the threshold routes through OCR."""
    import policyai_scrapers.ocr as ocr_mod

    monkeypatch.delenv("OCR_ENABLED", raising=False)
    sentinel = "OCR RECOVERED CIRCULAR TEXT " * 20
    monkeypatch.setattr(ocr_mod, "pdf_ocr_text", lambda data: sentinel)
    pdf = _scanned_pdf(("image only",))  # pypdf sees no text layer at all
    assert pdf_bytes_to_text(pdf) == sentinel


def test_pdf_bytes_to_text_ocr_disabled(monkeypatch):
    """OCR_ENABLED=0 restores the pypdf-only behaviour: no OCR call at all."""
    import policyai_scrapers.ocr as ocr_mod

    monkeypatch.setenv("OCR_ENABLED", "0")

    def _boom(data: bytes) -> str:
        raise AssertionError("OCR must not run when disabled")

    monkeypatch.setattr(ocr_mod, "pdf_ocr_text", _boom)
    pdf = _scanned_pdf(("image only",))
    text = pdf_bytes_to_text(pdf)
    assert len(text) < OCR_FALLBACK_CHARS  # the empty-ish pypdf result comes back


def test_pdf_bytes_to_text_keeps_pypdf_text_on_ocr_error(monkeypatch):
    """An OCR crash never loses the (thin) pypdf result."""
    import policyai_scrapers.ocr as ocr_mod

    monkeypatch.delenv("OCR_ENABLED", raising=False)

    def _boom(data: bytes) -> str:
        raise RuntimeError("model exploded")

    monkeypatch.setattr(ocr_mod, "pdf_ocr_text", _boom)
    pdf = _scanned_pdf(("image only",))
    assert pdf_bytes_to_text(pdf) == ""
