"""Unit tests for hybrid retrieval score fusion (docs/05-task.md Phase 10)."""

from retrieval_worker.fusion import reciprocal_rank_fusion, weighted_sum


def test_weighted_sum_prefers_chunk_strong_on_both_sides():
    dense = {"a": 0.9, "b": 0.5, "c": 0.1}
    sparse = {"a": 8.0, "b": 1.0, "c": 6.0}

    hits = weighted_sum(dense, sparse, dense_weight=0.7, sparse_weight=0.3)

    assert hits[0].chunk_id == "a"
    assert hits[0].dense_score == 0.9
    assert hits[0].sparse_score == 8.0


def test_weighted_sum_dense_only_weight_ignores_sparse():
    dense = {"a": 0.2, "b": 0.9}
    sparse = {"a": 100.0, "b": 0.0}

    hits = weighted_sum(dense, sparse, dense_weight=1.0, sparse_weight=0.0)

    assert hits[0].chunk_id == "b"


def test_weighted_sum_includes_chunks_from_either_side_only():
    dense = {"a": 0.8}
    sparse = {"b": 5.0}

    hits = weighted_sum(dense, sparse, dense_weight=0.5, sparse_weight=0.5)

    chunk_ids = {hit.chunk_id for hit in hits}
    assert chunk_ids == {"a", "b"}
    a_hit = next(hit for hit in hits if hit.chunk_id == "a")
    assert a_hit.sparse_score is None


def test_reciprocal_rank_fusion_rewards_consistent_top_ranking():
    dense = {"a": 0.9, "b": 0.8, "c": 0.1}
    sparse = {"a": 5.0, "b": 1.0, "c": 4.0}

    hits = reciprocal_rank_fusion(dense, sparse, k=60)

    assert hits[0].chunk_id == "a"


def test_reciprocal_rank_fusion_scores_are_bounded_and_positive():
    dense = {"a": 0.9}
    sparse = {"a": 5.0}

    hits = reciprocal_rank_fusion(dense, sparse, k=60)

    assert hits[0].fused_score == (1.0 / 61) + (1.0 / 61)
