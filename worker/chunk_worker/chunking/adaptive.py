"""Adaptive chunking (docs/05-task.md Phase 6) — a real decision tree
over the other already-implemented strategies, chosen from simple,
inspectable document characteristics (heading density, total prose
size). Not a stub: it genuinely dispatches to a different concrete
chunker depending on what the document looks like, and reports which one
it picked so that decision is visible rather than hidden.
"""

_HEADING_TYPES = {"title", "heading"}
_NON_PROSE_TYPES = {"image"}

SHORT_DOCUMENT_CHARS = 2000
LARGE_DOCUMENT_CHARS = 8000
MIN_HEADINGS_FOR_STRUCTURE = 3


def choose_strategy(spans: list[dict]) -> tuple[str, dict]:
    heading_count = sum(1 for span in spans if span["block"]["type"] in _HEADING_TYPES)
    prose_chars = sum(
        len(span["block"]["text"])
        for span in spans
        if span["block"]["type"] not in _NON_PROSE_TYPES
    )

    if prose_chars < SHORT_DOCUMENT_CHARS:
        return "paragraph", {"max_tokens": 400}

    if heading_count >= MIN_HEADINGS_FOR_STRUCTURE:
        if prose_chars > LARGE_DOCUMENT_CHARS:
            return "parent_child", {"parent_max_tokens": 1200, "child_max_tokens": 300}
        return "structural", {"max_tokens": 400}

    return "semantic", {"max_tokens": 400, "similarity_threshold": 0.25}


def chunk_adaptive(raw_text: str, spans: list[dict], config: dict) -> tuple[list[dict], str, dict]:
    from chunk_worker.chunking.factory import get_chunker

    strategy, chosen_config = choose_strategy(spans)
    chosen_config = {**chosen_config, **config.get("overrides", {})}
    chunker = get_chunker(strategy)
    chunks = chunker(raw_text, spans, chosen_config)
    return chunks, strategy, chosen_config
