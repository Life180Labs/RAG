"""Shared lightweight text utilities (docs/05-task.md Phase 12).

`split_sentences` was promoted here from `chunk_worker.chunking.text_utils`
(Phase 6) once `retrieval_worker`'s context compression (Phase 12,
docs/02-architecture.md section 75) needed the same sentence-boundary
splitting at retrieval time — the same "promote once a second package
has a real, present-tense need" pattern Phase 7's tokenizer and
embedding providers promotion already established.
`chunk_worker.chunking.text_utils` re-exports this so its existing
internal imports and tests are unaffected.
"""

import re

_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])")


def split_sentences(text: str) -> list[str]:
    """Regex-based sentence splitting — a lightweight heuristic (splits
    on `.`/`!`/`?` followed by whitespace and a capital letter/digit/
    quote) rather than a full NLP sentence tokenizer (nltk/spaCy). It
    under-handles abbreviations (e.g. "Dr. Smith") but needs no model
    download and no extra heavyweight dependency for what is, here, just
    a chunk-boundary/compression-scoring signal rather than downstream
    NLP analysis."""
    text = text.strip()
    if not text:
        return []
    sentences = _SENTENCE_BOUNDARY_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]
