"""Unit tests for MMR diversification (docs/05-task.md Phase 12;
docs/02-architecture.md section 62)."""

from retrieval_worker.mmr import RankedCandidate, parse_vector_text, select


def test_parse_vector_text_round_trips_pgvector_format():
    assert parse_vector_text("[0.1,0.2,0.3]") == [0.1, 0.2, 0.3]


def test_select_prefers_diverse_candidate_over_near_duplicate():
    # "a" and "b" are near-identical vectors (both about relevance 0.9);
    # "c" is orthogonal to both with slightly lower relevance. With
    # lambda=0.5, after picking "a" first, MMR should prefer the
    # diverse "c" over the redundant near-duplicate "b" for the second
    # slot, even though "b" alone has higher raw relevance than "c".
    candidates = [
        RankedCandidate(chunk_id="a", score=0.95),
        RankedCandidate(chunk_id="b", score=0.90),
        RankedCandidate(chunk_id="c", score=0.60),
    ]
    vectors = {
        "a": [1.0, 0.0],
        "b": [0.99, 0.01],
        "c": [0.0, 1.0],
    }
    selected = select(candidates, vectors, top_k=2, lambda_param=0.5)
    assert [c.chunk_id for c in selected] == ["a", "c"]


def test_select_respects_top_k():
    candidates = [RankedCandidate(chunk_id=str(i), score=1.0 - i * 0.1) for i in range(5)]
    vectors = {str(i): [float(i), 0.0] for i in range(5)}
    selected = select(candidates, vectors, top_k=3, lambda_param=0.7)
    assert len(selected) == 3


def test_select_preserves_original_relevance_score():
    candidates = [RankedCandidate(chunk_id="a", score=0.42)]
    selected = select(candidates, {"a": [1.0, 0.0]}, top_k=1, lambda_param=0.5)
    assert selected[0].score == 0.42


def test_select_handles_missing_vectors_gracefully():
    candidates = [
        RankedCandidate(chunk_id="a", score=0.9),
        RankedCandidate(chunk_id="b", score=0.8),
    ]
    selected = select(candidates, {}, top_k=2, lambda_param=0.5)
    assert {c.chunk_id for c in selected} == {"a", "b"}


def test_lambda_one_reduces_to_pure_relevance_order():
    candidates = [
        RankedCandidate(chunk_id="a", score=0.5),
        RankedCandidate(chunk_id="b", score=0.9),
    ]
    vectors = {"a": [1.0, 0.0], "b": [1.0, 0.0]}
    selected = select(candidates, vectors, top_k=2, lambda_param=1.0)
    assert [c.chunk_id for c in selected] == ["b", "a"]
