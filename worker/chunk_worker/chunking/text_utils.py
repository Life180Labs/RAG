"""Shared helpers for turning Phase 5's `structured_content` blocks into
character-offset-tracked text, and for splitting text into sentences.

Every chunker ultimately produces `char_start`/`char_end` offsets into
the *same* joined string this module builds — the same "\\n\\n"-joined
non-image text that `document_content.raw_text` already is (see
worker/document_worker/parsing/metadata.py `join_text`) — so a chunk's
offsets are meaningful against the document's raw text a UI could
display alongside it.
"""

import re

from common.tokenizer import count_tokens

_NON_PROSE_TYPES = {"image"}
_HEADING_TYPES = {"title", "heading"}
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])")


def join_blocks_with_spans(blocks: list[dict]) -> tuple[str, list[dict]]:
    """Returns `(raw_text, spans)` where `spans[i]` describes
    `blocks[i]`'s location: `{"block": block, "start": int, "end": int,
    "heading": str | None}`. `heading` is the nearest preceding
    title/heading block's text (the block's own heading, if it is one).
    Image blocks are skipped (they contribute no text) but still appear
    in `spans` with `start == end` so index-based lookups stay aligned.
    """
    parts: list[str] = []
    spans: list[dict] = []
    cursor = 0
    current_heading: str | None = None

    for block in blocks:
        if block["type"] in _HEADING_TYPES:
            # Some parsers' heading-detection heuristics (e.g. PDF font-size
            # based) occasionally misclassify a long body paragraph as a
            # heading-type block. Capped to fit `chunks.heading`'s
            # VARCHAR(500) column — a "heading" longer than that isn't a
            # real heading anyway, so truncating here (rather than at
            # insert time) keeps every chunker's output already valid.
            current_heading = block["text"][:500]

        if block["type"] in _NON_PROSE_TYPES:
            spans.append(
                {"block": block, "start": cursor, "end": cursor, "heading": current_heading}
            )
            continue

        if parts:
            parts.append("\n\n")
            cursor += 2

        start = cursor
        parts.append(block["text"])
        cursor += len(block["text"])
        spans.append({"block": block, "start": start, "end": cursor, "heading": current_heading})

    return "".join(parts), spans


def context_at(offset: int, spans: list[dict]) -> tuple[int | None, str | None]:
    """Returns `(page, heading)` for whichever span contains `offset`
    (or the last span starting at-or-before it, for an offset that
    lands exactly on a boundary)."""
    context = (None, None)
    for span in spans:
        if span["start"] <= offset < span["end"] or span["start"] == offset:
            block = span["block"]
            return block.get("page"), span["heading"]
        if span["start"] <= offset:
            block = span["block"]
            context = (block.get("page"), span["heading"])
    return context


def make_chunk(
    raw_text: str, start: int, end: int, spans: list[dict], *, parent_ref: int | None = None
) -> dict:
    """Builds the common chunk dict every strategy produces. `parent_ref`
    is an index into that same chunker's own output list (resolved to a
    real `parent_chunk_id` UUID by the Celery task after insertion), used
    by the parent_child/hierarchical strategies only."""
    text = raw_text[start:end].strip()
    stripped_start = start + (raw_text[start:end].find(text) if text else 0)
    page, heading = context_at(stripped_start, spans)
    return {
        "text": text,
        "char_start": stripped_start,
        "char_end": stripped_start + len(text),
        "token_count": count_tokens(text),
        "page": page,
        "heading": heading,
        "parent_ref": parent_ref,
    }


def merge_units_to_chunks(
    raw_text: str,
    units: list[tuple[int, int]],
    spans: list[dict],
    max_tokens: int,
    *,
    force_break_before: set[int] | None = None,
) -> list[dict]:
    """Greedily merges consecutive `(start, end)` units — paragraphs,
    sentences, whatever granularity the caller wants — into chunks that
    stay under `max_tokens`, flushing early at any unit index in
    `force_break_before` (used by the structural chunker to always start
    a new chunk at a heading, regardless of the token budget)."""
    force_break_before = force_break_before or set()
    chunks: list[dict] = []
    current_start: int | None = None
    current_end: int | None = None
    current_tokens = 0

    for index, (unit_start, unit_end) in enumerate(units):
        unit_tokens = count_tokens(raw_text[unit_start:unit_end])

        should_break = current_start is not None and (
            index in force_break_before or current_tokens + unit_tokens > max_tokens
        )
        if should_break:
            chunk = make_chunk(raw_text, current_start, current_end, spans)
            if chunk["text"]:
                chunks.append(chunk)
            current_start = None

        if current_start is None:
            current_start, current_end, current_tokens = unit_start, unit_end, unit_tokens
        else:
            current_end = unit_end
            current_tokens += unit_tokens

    if current_start is not None:
        chunk = make_chunk(raw_text, current_start, current_end, spans)
        if chunk["text"]:
            chunks.append(chunk)

    return chunks


def split_sentences(text: str) -> list[str]:
    """Regex-based sentence splitting — a lightweight heuristic (splits
    on `.`/`!`/`?` followed by whitespace and a capital letter/digit/
    quote) rather than a full NLP sentence tokenizer (nltk/spaCy). It
    under-handles abbreviations (e.g. "Dr. Smith") but needs no model
    download and no extra heavyweight dependency for what is, here, just
    a chunk-boundary signal rather than downstream NLP analysis."""
    text = text.strip()
    if not text:
        return []
    sentences = _SENTENCE_BOUNDARY_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]
