"""Cleaning pipeline (docs/02-architecture.md section 27/28) — unicode
normalization, smart-quote/dash normalization, whitespace collapsing, and
removal of page numbers and repeated headers/footers.

Table/code/image blocks are left untouched: they're structured or
verbatim content, not prose, so "cleaning" them would corrupt them.
"""

import re
import unicodedata
from collections import Counter

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_PAGE_NUMBER_RE = re.compile(r"^\s*(page\s+)?\d+\s*(of\s+\d+)?\s*$", re.IGNORECASE)

_SMART_CHAR_MAP = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "…": "...",
}

_PROSE_TYPES = {"title", "heading", "paragraph", "list"}
_BOILERPLATE_MAX_CHARS = 200
_MIN_REPEAT_COUNT = 3


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for smart_char, plain_char in _SMART_CHAR_MAP.items():
        text = text.replace(smart_char, plain_char)
    text = _CONTROL_CHARS_RE.sub("", text)
    text = text.replace("\t", " ")
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def clean_blocks(blocks: list[dict]) -> list[dict]:
    line_counts: Counter[str] = Counter()
    for block in blocks:
        if block["type"] not in _PROSE_TYPES:
            continue
        stripped = block["text"].strip()
        if stripped and len(stripped) < _BOILERPLATE_MAX_CHARS:
            line_counts[stripped] += 1

    repeated_lines = {line for line, count in line_counts.items() if count >= _MIN_REPEAT_COUNT}

    cleaned: list[dict] = []
    for block in blocks:
        if block["type"] not in _PROSE_TYPES:
            cleaned.append(block)
            continue

        stripped = block["text"].strip()
        if not stripped or _PAGE_NUMBER_RE.match(stripped) or stripped in repeated_lines:
            continue

        normalized = dict(block)
        normalized["text"] = normalize_text(block["text"])
        if normalized["text"]:
            cleaned.append(normalized)

    return cleaned
