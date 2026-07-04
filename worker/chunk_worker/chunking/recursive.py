"""Recursive chunking (docs/02-architecture.md section 34) — the
preferred default. Tries to keep each block (paragraph/list/etc.)
whole; only when a single block exceeds the token budget does it fall
back to splitting that block at sentence boundaries, and only when a
single sentence still exceeds the budget does it fall back further to
word boundaries — preserving the largest semantic unit that fits,
document -> section -> paragraph -> sentence -> words, per the
architecture doc's priority order.

Table/code blocks are never split at sentence/word level even if they
exceed the budget — splitting a table mid-row or code mid-statement
would destroy more meaning than an oversized chunk preserves.
"""

from chunk_worker.chunking.text_utils import merge_units_to_chunks, split_sentences
from common.tokenizer import count_tokens

DEFAULT_MAX_TOKENS = 400
_NON_SPLITTABLE_TYPES = {"table", "code"}


def _split_oversized_sentence(text: str, start: int, max_tokens: int) -> list[tuple[int, int]]:
    words = text.split(" ")
    units: list[tuple[int, int]] = []
    cursor = start
    buffer = ""
    buffer_start = start

    for word in words:
        candidate = f"{buffer} {word}".strip() if buffer else word
        if buffer and count_tokens(candidate) > max_tokens:
            units.append((buffer_start, buffer_start + len(buffer)))
            cursor = buffer_start + len(buffer) + 1
            buffer = word
            buffer_start = cursor
        else:
            buffer = candidate

    if buffer:
        units.append((buffer_start, buffer_start + len(buffer)))
    return units


def _atomic_units(raw_text: str, spans: list[dict], max_tokens: int) -> list[tuple[int, int]]:
    units: list[tuple[int, int]] = []

    for span in spans:
        block = span["block"]
        block_type = block["type"]
        if block_type == "image":
            continue

        block_start, block_end = span["start"], span["end"]
        block_text = raw_text[block_start:block_end]

        if count_tokens(block_text) <= max_tokens or block_type in _NON_SPLITTABLE_TYPES:
            units.append((block_start, block_end))
            continue

        search_from = 0
        for sentence in split_sentences(block_text):
            offset = block_text.index(sentence, search_from)
            sentence_start = block_start + offset
            if count_tokens(sentence) <= max_tokens:
                units.append((sentence_start, sentence_start + len(sentence)))
            else:
                units.extend(_split_oversized_sentence(sentence, sentence_start, max_tokens))
            search_from = offset + len(sentence)

    return units


def chunk_recursive(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
    units = _atomic_units(raw_text, spans, max_tokens)
    return merge_units_to_chunks(raw_text, units, spans, max_tokens)
