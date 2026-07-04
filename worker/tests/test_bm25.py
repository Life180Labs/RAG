"""Unit tests for BM25 sparse retrieval (docs/05-task.md Phase 10)."""

from retrieval_worker.bm25 import search


def test_bm25_ranks_exact_term_match_first():
    chunks = [
        ("a", "The quick brown fox jumps over the lazy dog."),
        ("b", "Error code XJ-9042 was raised during checkout."),
        ("c", "A completely unrelated sentence about weather."),
    ]
    hits = search(chunks, "XJ-9042 error checkout", top_k=3)

    assert hits[0].chunk_id == "b"
    assert hits[0].score > 0


def test_bm25_excludes_zero_score_hits():
    # A tiny (2-document) corpus makes BM25's IDF unstable — a term
    # appearing in most of the corpus can legitimately score at or
    # below zero. Five distractor documents keep the corpus large
    # enough for the term-overlap chunk's score to be reliably positive
    # while the completely unrelated chunk still scores zero.
    chunks = [
        ("a", "Vector databases support cosine similarity search."),
        ("b", "This chunk shares absolutely no terms with the query at all."),
        ("c", "Enterprise software licensing agreements and compliance."),
        ("d", "The weather forecast predicts rain for the weekend."),
        ("e", "A recipe for baking sourdough bread at home."),
        ("f", "Quarterly financial results exceeded expectations."),
    ]
    hits = search(chunks, "cosine similarity vector", top_k=10)

    chunk_ids = [hit.chunk_id for hit in hits]
    assert "a" in chunk_ids
    assert "b" not in chunk_ids


def test_bm25_returns_empty_for_empty_corpus():
    assert search([], "anything", top_k=5) == []


def test_bm25_returns_empty_for_blank_query():
    chunks = [("a", "some text")]
    assert search(chunks, "   ", top_k=5) == []


def test_bm25_respects_top_k():
    chunks = [(str(i), f"shared keyword occurrence number {i}") for i in range(10)]
    hits = search(chunks, "shared keyword", top_k=3)
    assert len(hits) == 3
