"""Parent-Child context expansion (docs/05-task.md Phase 12;
docs/02-architecture.md section 63 Parent-Child Retrieval).

Search always happens on whatever chunk actually matched (the small
"child" chunk, if the chunk set was built with the `parent_child`
strategy — see docs/05-task.md Phase 6) — this module only remaps the
*returned* identity from a matched child to its parent afterward, per
the architecture doc's "search on children, return the parent" split.
Chunk sets built with any other strategy have no `parent_chunk_id` on
their rows, so expansion is a no-op for them (every chunk maps to
itself), which is why this is safe to enable unconditionally rather
than needing to check the chunk set's strategy first.

Merging by max score (not summing or averaging) mirrors the same
max-score merge Phase 11 uses across multi-query variants — expanding
two child hits that share one parent should show that parent once, at
its best-scoring child's rank, not double-counted.
"""


def expand(
    results: list[dict], parent_by_chunk_id: dict[str, str | None]
) -> list[dict]:
    """`results` is a list of result dicts (each with at least
    `"chunk_id"` and `"score"` keys — `execute_retrieval`'s dense/sparse
    score attributions ride along on the rest of each dict).
    `parent_by_chunk_id[chunk_id]` is that chunk's `parent_chunk_id` (or
    `None`/absent if it has no parent, including chunks from non-
    parent_child chunk sets). Returns a new list with each result's
    `chunk_id` remapped to its parent where one exists, and duplicates
    that land on the same resulting id merged by keeping the
    highest-scoring one whole (so its dense_score/sparse_score stay
    consistent with the score that won, rather than being averaged or
    dropped).
    """
    best_by_key: dict[str, dict] = {}
    for result in results:
        target = parent_by_chunk_id.get(result["chunk_id"]) or result["chunk_id"]
        if target not in best_by_key or result["score"] > best_by_key[target]["score"]:
            merged = dict(result)
            merged["chunk_id"] = target
            best_by_key[target] = merged
    return list(best_by_key.values())
