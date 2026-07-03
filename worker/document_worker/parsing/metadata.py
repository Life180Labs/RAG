"""Metadata extraction (docs/02-architecture.md section 29) — language
detection, word/character counts, and estimated reading time."""

import langdetect
from langdetect.lang_detect_exception import LangDetectException

_WORDS_PER_MINUTE = 200
_LANGUAGE_SAMPLE_CHARS = 2000
_NON_PROSE_TYPES = {"image"}


def join_text(blocks: list[dict]) -> str:
    return "\n\n".join(block["text"] for block in blocks if block["type"] not in _NON_PROSE_TYPES)


def detect_language(text: str) -> str | None:
    sample = text[:_LANGUAGE_SAMPLE_CHARS].strip()
    if not sample:
        return None
    try:
        return langdetect.detect(sample)
    except LangDetectException:
        return None


def compute_metadata(blocks: list[dict], page_count: int | None) -> dict:
    raw_text = join_text(blocks)
    word_count = len(raw_text.split())
    character_count = len(raw_text)
    reading_time_seconds = max(1, round(word_count / _WORDS_PER_MINUTE * 60)) if word_count else 0

    return {
        "raw_text": raw_text,
        "word_count": word_count,
        "character_count": character_count,
        "reading_time_seconds": reading_time_seconds,
        "language": detect_language(raw_text),
        "page_count": page_count,
    }
