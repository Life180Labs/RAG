"""Maximum Marginal Relevance diversification (docs/05-task.md Phase 12;
docs/02-architecture.md section 62 Diversity Optimization).

Real greedy MMR over each candidate's actual embedding vector (fetched
from the `embeddings` table `execute_retrieval` already has access to
for the same embedding_version) — not an approximation over just the
scalar relevance scores, since MMR's whole point is trading relevance
against *semantic* similarity to what's already been selected.

No numpy dependency: cosine similarity between two same-length float
lists is a handful of `sum()`/`math.sqrt()` calls, and these vectors
are already zero-padded to a fixed width (`embedding.py`'s
`EMBEDDING_DIM_MAX`) — trailing zero components contribute nothing to
either the dot product or either vector's norm, so comparing the full
padded vectors gives an identical result to comparing just the real
`dimensions` prefix, without needing to know `dimensions` here at all.
"""

import math
from dataclasses import dataclass


def parse_vector_text(value: str) -> list[float]:
    # Same manual parsing `index_worker.tasks._parse_vector_text` uses —
    # pgvector's text representation is "[0.1,0.2,...]" and no pgvector
    # adapter is registered on this sync engine.
    return [float(x) for x in value.strip("[]").split(",")]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class RankedCandidate:
    chunk_id: str
    score: float


def select(
    candidates: list[RankedCandidate],
    vectors: dict[str, list[float]],
    top_k: int,
    lambda_param: float,
) -> list[RankedCandidate]:
    """Greedily selects up to `top_k` candidates from `candidates`
    (assumed already sorted by relevance, most relevant first),
    maximizing `lambda_param * relevance - (1 - lambda_param) *
    max_similarity_to_already_selected` at each step. A candidate
    missing a vector (shouldn't normally happen — every candidate came
    from this same embedding_version) is treated as having zero
    similarity to anything, so it can't be penalized for diversity but
    also can't be boosted by it.

    Returns candidates in MMR-selected order with their *original*
    relevance score (not the blended MMR score, which isn't a
    similarity in the same units and isn't meant to be persisted).
    """
    remaining = list(candidates)
    selected: list[RankedCandidate] = []

    while remaining and len(selected) < top_k:
        best_index = 0
        best_mmr_score = float("-inf")
        for index, candidate in enumerate(remaining):
            vector = vectors.get(candidate.chunk_id)
            if vector is None or not selected:
                diversity_penalty = 0.0
            else:
                diversity_penalty = max(
                    (
                        _cosine_similarity(vector, vectors[sel.chunk_id])
                        for sel in selected
                        if sel.chunk_id in vectors
                    ),
                    default=0.0,
                )
            mmr_score = lambda_param * candidate.score - (1 - lambda_param) * diversity_penalty
            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_index = index
        selected.append(remaining.pop(best_index))

    return selected
