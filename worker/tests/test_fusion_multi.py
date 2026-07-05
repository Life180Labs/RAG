"""Unit tests for N-way RRF (docs/05-task.md Phase 12; docs/02-architecture.md
section 103 RAG Fusion). See test_fusion.py for the existing 2-list
`reciprocal_rank_fusion` coverage, unchanged by this addition.
"""

from retrieval_worker.fusion import reciprocal_rank_fusion_multi


def test_matches_two_way_rrf_when_given_exactly_two_lists():
    from retrieval_worker.fusion import reciprocal_rank_fusion

    dense = {"a": 0.9, "b": 0.5, "c": 0.1}
    sparse = {"b": 5.0, "c": 2.0}

    two_way = reciprocal_rank_fusion(dense, sparse, k=60)
    multi = reciprocal_rank_fusion_multi([dense, sparse], k=60)

    two_way_scores = {hit.chunk_id: hit.fused_score for hit in two_way}
    multi_scores = {hit.chunk_id: hit.fused_score for hit in multi}
    assert two_way_scores == multi_scores


def test_chunk_appearing_in_more_lists_ranks_higher():
    # "a" appears at rank 1 in three lists; "b" appears at rank 1 in
    # only one list and is absent from the others — RRF should prefer
    # the chunk with broader cross-list support.
    lists = [
        {"a": 1.0, "b": 0.1},
        {"a": 1.0},
        {"a": 1.0, "c": 0.5},
    ]
    fused = reciprocal_rank_fusion_multi(lists, k=60)
    assert fused[0].chunk_id == "a"


def test_leaves_component_scores_none():
    fused = reciprocal_rank_fusion_multi([{"a": 1.0}, {"a": 0.5}], k=60)
    assert fused[0].dense_score is None
    assert fused[0].sparse_score is None


def test_returns_empty_for_empty_input():
    assert reciprocal_rank_fusion_multi([], k=60) == []
