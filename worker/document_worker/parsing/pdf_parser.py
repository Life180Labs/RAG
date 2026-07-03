"""PDF parser (PyMuPDF/fitz) — docs/02-architecture.md section 25/30.

Structure is inferred from font metrics rather than flattened to plain
text: each native PyMuPDF text block becomes one "paragraph" or "heading"
block (heading = its largest span is notably bigger than the page's
modal font size), monospace-font blocks become "code", bullet/numbered
lines become "list", real tables are detected via `page.find_tables()`,
and image XObjects become "image" placeholders. The first heading found
in the document is promoted to "title".
"""

import re
import statistics

import fitz

_LIST_PREFIX_RE = re.compile(r"^\s*([-*•‣◦]|\d+[.)])\s+")
_MONOSPACE_HINTS = ("mono", "courier", "consolas", "menlo")
_HEADING_SIZE_RATIO = 1.3


def _is_monospace(font_name: str) -> bool:
    lowered = font_name.lower()
    return any(hint in lowered for hint in _MONOSPACE_HINTS)


def parse(content: bytes) -> tuple[list[dict], int]:
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        blocks: list[dict] = []
        title_assigned = False

        for page_index in range(doc.page_count):
            page = doc[page_index]
            page_number = page_index + 1

            try:
                for table in page.find_tables():
                    rows = table.extract()
                    text = "\n".join(
                        " | ".join("" if cell is None else str(cell) for cell in row)
                        for row in rows
                    )
                    if text.strip():
                        blocks.append(
                            {"type": "table", "text": text, "level": None, "page": page_number}
                        )
            except Exception:  # noqa: BLE001 - table detection is best-effort
                pass

            text_dict = page.get_text("dict")
            font_sizes = [
                span["size"]
                for block in text_dict["blocks"]
                if block.get("type") == 0
                for line in block["lines"]
                for span in line["spans"]
            ]
            median_size = statistics.median(font_sizes) if font_sizes else 0

            for block in text_dict["blocks"]:
                if block.get("type") == 1:
                    blocks.append(
                        {"type": "image", "text": "[Image]", "level": None, "page": page_number}
                    )
                    continue

                line_texts = []
                max_size = 0.0
                all_monospace = True
                for line in block.get("lines", []):
                    line_text = "".join(span["text"] for span in line["spans"])
                    if line_text.strip():
                        line_texts.append(line_text.strip())
                    for span in line["spans"]:
                        max_size = max(max_size, span["size"])
                        if span["text"].strip() and not _is_monospace(span["font"]):
                            all_monospace = False

                text = " ".join(line_texts).strip()
                if not text:
                    continue

                if all_monospace and line_texts:
                    block_type, level = "code", None
                elif _LIST_PREFIX_RE.match(text):
                    block_type, level = "list", None
                elif median_size and max_size >= median_size * _HEADING_SIZE_RATIO:
                    block_type, level = ("title", None) if not title_assigned else ("heading", 1)
                    title_assigned = True
                else:
                    block_type, level = "paragraph", None

                blocks.append(
                    {"type": block_type, "text": text, "level": level, "page": page_number}
                )

        return blocks, doc.page_count
    finally:
        doc.close()
