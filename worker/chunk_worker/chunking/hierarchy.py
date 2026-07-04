"""Parent-child and hierarchical chunking (docs/02-architecture.md
sections 36-37). Parent-child is a 2-level tree (section-sized parents,
each with recursively-chunked children); hierarchical is the same idea
generalized to N levels with shrinking token budgets per level —
parent-child is implemented as `chunk_hierarchical` with `max_depth=2`
rather than duplicated logic.

`parent_ref` on each returned chunk is an index into this function's own
output list (resolved to a real `parent_chunk_id` UUID by the Celery
task once rows exist), matching the convention used by every chunker.
"""

from chunk_worker.chunking.structural import chunk_structural

DEFAULT_PARENT_MAX_TOKENS = 1200
DEFAULT_CHILD_MAX_TOKENS = 300
DEFAULT_TOP_LEVEL_BUDGET = 1600
DEFAULT_LEVEL_SHRINK_FACTOR = 3
DEFAULT_MIN_LEVEL_BUDGET = 150


def _sub_spans(spans: list[dict], char_start: int, char_end: int) -> list[dict]:
    return [s for s in spans if s["start"] >= char_start and s["end"] <= char_end]


def chunk_parent_child(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.recursive import chunk_recursive

    parent_max_tokens = config.get("parent_max_tokens", DEFAULT_PARENT_MAX_TOKENS)
    child_max_tokens = config.get("child_max_tokens", DEFAULT_CHILD_MAX_TOKENS)

    parents = chunk_structural(raw_text, spans, {"max_tokens": parent_max_tokens})

    result: list[dict] = []
    for parent in parents:
        parent_copy = dict(parent)
        parent_copy["parent_ref"] = None
        result.append(parent_copy)
        parent_position = len(result) - 1

        children_spans = _sub_spans(spans, parent["char_start"], parent["char_end"])
        if not children_spans:
            continue

        children = chunk_recursive(raw_text, children_spans, {"max_tokens": child_max_tokens})
        for child in children:
            child_copy = dict(child)
            child_copy["parent_ref"] = parent_position
            result.append(child_copy)

    return result


def _default_level_budgets(max_depth: int) -> list[int]:
    budgets = []
    budget = DEFAULT_TOP_LEVEL_BUDGET
    for _ in range(max_depth):
        budgets.append(budget)
        budget = max(DEFAULT_MIN_LEVEL_BUDGET, budget // DEFAULT_LEVEL_SHRINK_FACTOR)
    return budgets


def chunk_hierarchical(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.recursive import chunk_recursive

    max_depth = max(1, config.get("max_depth", 3))
    level_budgets = config.get("level_token_budgets") or _default_level_budgets(max_depth)

    result: list[dict] = []

    def build_level(depth: int, budget: int, remaining: list[int], span_subset, parent_position):
        is_leaf_level = not remaining
        chunker = chunk_recursive if is_leaf_level else chunk_structural
        chunks_at_level = chunker(raw_text, span_subset, {"max_tokens": budget})

        # A single chunk covering the whole subset means this branch has
        # nothing left to structurally subdivide — recursing further would
        # just produce an identical duplicate "child", so stop here.
        can_recurse = remaining and len(chunks_at_level) > 1

        for chunk in chunks_at_level:
            chunk_copy = dict(chunk)
            chunk_copy["parent_ref"] = parent_position
            result.append(chunk_copy)
            this_position = len(result) - 1

            if can_recurse:
                sub_spans = _sub_spans(span_subset, chunk["char_start"], chunk["char_end"])
                if sub_spans:
                    build_level(depth + 1, remaining[0], remaining[1:], sub_spans, this_position)

    build_level(0, level_budgets[0], level_budgets[1:], spans, None)
    return result
