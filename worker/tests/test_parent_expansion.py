"""Unit tests for parent-child context expansion (docs/05-task.md
Phase 12; docs/02-architecture.md section 63)."""

from retrieval_worker.parent_expansion import expand


def test_remaps_child_to_parent_when_parent_exists():
    results = [{"chunk_id": "child-1", "score": 0.9, "dense_score": 0.9, "sparse_score": None}]
    parent_map = {"child-1": "parent-a"}
    expanded = expand(results, parent_map)
    assert expanded == [{"chunk_id": "parent-a", "score": 0.9, "dense_score": 0.9,
                          "sparse_score": None}]


def test_leaves_chunk_unchanged_when_no_parent():
    results = [{"chunk_id": "solo-1", "score": 0.7, "dense_score": None, "sparse_score": None}]
    expanded = expand(results, {"solo-1": None})
    assert expanded[0]["chunk_id"] == "solo-1"


def test_leaves_chunk_unchanged_when_missing_from_parent_map():
    # A chunk from a non-parent_child chunk set (or otherwise absent
    # from the map) has no entry at all — must still pass through.
    results = [{"chunk_id": "x", "score": 0.5, "dense_score": None, "sparse_score": None}]
    expanded = expand(results, {})
    assert expanded[0]["chunk_id"] == "x"


def test_two_children_of_same_parent_merge_keeping_best_score():
    results = [
        {"chunk_id": "child-1", "score": 0.6, "dense_score": 0.6, "sparse_score": None},
        {"chunk_id": "child-2", "score": 0.9, "dense_score": 0.9, "sparse_score": None},
    ]
    parent_map = {"child-1": "parent-a", "child-2": "parent-a"}
    expanded = expand(results, parent_map)
    assert len(expanded) == 1
    assert expanded[0]["chunk_id"] == "parent-a"
    assert expanded[0]["score"] == 0.9
    assert expanded[0]["dense_score"] == 0.9


def test_returns_empty_for_empty_input():
    assert expand([], {}) == []
