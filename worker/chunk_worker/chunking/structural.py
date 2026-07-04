"""Structural chunking (docs/02-architecture.md section 32) — splits at
every heading/title boundary, in addition to the normal token budget.

Registered under both the "markdown" and "html" strategy names: once
Phase 5 has parsed a document into `structured_content` blocks, there is
no format-specific information left to differentiate a "Markdown
chunker" from an "HTML chunker" — both source formats converge to the
same heading/paragraph/list/table/code/image block representation, so a
single algorithm genuinely serves both rather than two copies of the
same code.
"""

DEFAULT_MAX_TOKENS = 400
_HEADING_TYPES = {"title", "heading"}
_NON_PROSE_TYPES = {"image"}


def chunk_structural(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.text_utils import merge_units_to_chunks

    max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
    units: list[tuple[int, int]] = []
    force_break_before: set[int] = set()

    for span in spans:
        block = span["block"]
        if block["type"] in _NON_PROSE_TYPES:
            continue
        if block["type"] in _HEADING_TYPES and units:
            force_break_before.add(len(units))
        units.append((span["start"], span["end"]))

    return merge_units_to_chunks(
        raw_text, units, spans, max_tokens, force_break_before=force_break_before
    )
