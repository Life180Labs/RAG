"""BM25 sparse retrieval (docs/05-task.md Phase 10; docs/02-architecture.md
section 57 Sparse Retrieval).

Computed fresh per query directly over a chunk_set's READY chunk texts
via `rank_bm25` (a real BM25Okapi implementation, not an approximation)
rather than a persisted inverted index — chunk sets in this system are
individual documents, not a web-scale corpus, so re-tokenizing and
scoring the whole set per query is fast and avoids maintaining a second
index artifact that would need to stay in sync with chunk regeneration
the same way vector indexes already must (docs/03-database.md section
18).
"""

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


@dataclass
class SparseHit:
    chunk_id: str
    score: float


def search(chunks: list[tuple[str, str]], query_text: str, top_k: int) -> list[SparseHit]:
    """`chunks` is a list of (chunk_id, text) pairs to rank against.
    Returns up to `top_k` hits ordered by BM25 score descending,
    excluding zero-score hits (no term overlap with the query at all —
    a real BM25 score of exactly 0, not a filtered-out candidate)."""
    if not chunks or not query_text.strip():
        return []

    corpus = [_tokenize(text) for _, text in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query_text))

    ranked = sorted(zip(chunks, scores, strict=True), key=lambda pair: pair[1], reverse=True)
    return [
        SparseHit(chunk_id=chunk_id, score=float(score))
        for (chunk_id, _text), score in ranked[:top_k]
        if score > 0
    ]
