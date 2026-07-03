"""OCR pipeline (Tesseract), docs/02-architecture.md section 26.

Only PDF pages that PyMuPDF extracted essentially no text from (scanned
pages, photographed pages, etc.) are rasterized and OCR'd — a page with a
real text layer is never re-OCR'd, since that would just re-derive worse
text from a raster of already-correct text.

EasyOCR/PaddleOCR/cloud OCR providers are documented alternatives in the
architecture doc but not implemented here — Tesseract is the one real,
tested engine for this phase, matching the pattern established in Phase
4 (implement one real path, document the rest as deferred) rather than
stubbing out three engines nobody has verified.
"""

import statistics

import pytesseract
from pdf2image import convert_from_bytes

MIN_TEXT_CHARS_PER_PAGE = 20


def page_needs_ocr(page_text: str) -> bool:
    return len(page_text.strip()) < MIN_TEXT_CHARS_PER_PAGE


def ocr_pdf_pages(content: bytes, page_numbers: list[int]) -> dict[int, tuple[str, float]]:
    """OCRs the given 1-indexed PDF page numbers. Returns
    `{page_number: (text, average_confidence_0_to_100)}`."""
    if not page_numbers:
        return {}

    first_page, last_page = min(page_numbers), max(page_numbers)
    images = convert_from_bytes(content, first_page=first_page, last_page=last_page)

    results: dict[int, tuple[str, float]] = {}
    for page_number in page_numbers:
        image = images[page_number - first_page]
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        words = []
        confidences = []
        for word, conf in zip(data["text"], data["conf"], strict=True):
            if not word.strip():
                continue
            words.append(word)
            confidence = float(conf)
            if confidence >= 0:
                confidences.append(confidence)

        text = " ".join(words)
        confidence = statistics.mean(confidences) if confidences else 0.0
        results[page_number] = (text, confidence)

    return results
