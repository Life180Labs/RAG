"""Paragraph chunking (docs/02-architecture.md section 32) — merges
consecutive structural blocks (paragraphs, list items, table/code blocks
count as their own unit too) up to a token budget, never splitting a
block itself."""

DEFAULT_MAX_TOKENS = 400

_NON_PROSE_TYPES = {"image"}


def chunk_paragraph(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.text_utils import merge_units_to_chunks

    max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
    units = [
        (span["start"], span["end"])
        for span in spans
        if span["block"]["type"] not in _NON_PROSE_TYPES
    ]
    return merge_units_to_chunks(raw_text, units, spans, max_tokens)
