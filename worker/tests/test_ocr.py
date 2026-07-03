"""OCR tests — skipped unless the `tesseract` and `pdftoppm` (poppler)
binaries are actually installed, since pytesseract/pdf2image are thin
wrappers around those system executables. The dockerized worker image
installs both (see worker/Dockerfile.dev); a bare local venv on a
developer machine typically won't, so these are exercised for real
inside the container rather than mocked out here.
"""

import shutil

import fitz
import pytest

from document_worker.parsing import ocr

pytestmark = pytest.mark.skipif(
    shutil.which("tesseract") is None or shutil.which("pdftoppm") is None,
    reason="tesseract/poppler not installed on this host — run inside the worker container",
)


def _scanned_pdf_bytes(text: str) -> bytes:
    """Builds a PDF with no text layer at all — a page rendered as a raw
    image, exactly like a scanned document — so `pdf_parser` extracts zero
    text and the OCR path is the only way to recover the content."""
    doc = fitz.open()
    text_page = doc.new_page()
    text_page.insert_text((72, 72), text, fontsize=28)
    pixmap = text_page.get_pixmap(dpi=200)
    image_bytes = pixmap.tobytes("png")
    doc.close()

    scanned_doc = fitz.open()
    scanned_page = scanned_doc.new_page(width=pixmap.width, height=pixmap.height)
    scanned_page.insert_image(scanned_page.rect, stream=image_bytes)
    result = scanned_doc.tobytes()
    scanned_doc.close()
    return result


def test_page_needs_ocr_true_for_near_empty_text():
    assert ocr.page_needs_ocr("") is True
    assert ocr.page_needs_ocr("   \n  ") is True
    assert ocr.page_needs_ocr("short") is True


def test_page_needs_ocr_false_for_real_text():
    assert ocr.page_needs_ocr("a" * 200) is False


def test_ocr_pdf_pages_recovers_text_from_scanned_page():
    pdf_bytes = _scanned_pdf_bytes("HELLO OCR WORLD")

    results = ocr.ocr_pdf_pages(pdf_bytes, [1])

    assert 1 in results
    text, confidence = results[1]
    assert "HELLO" in text.upper()
    assert confidence > 0
