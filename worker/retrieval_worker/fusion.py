"""Score fusion for hybrid retrieval (docs/05-task.md Phase 10;
docs/02-architecture.md section 58 Hybrid Search).

Two real fusion strategies, matching task.md's Fusion deliverables:

- Weighted sum: min-max normalizes each side to [0, 1] first, since
  dense similarity (roughly [-1, 1] for cosine) and BM25 (unbounded,
  corpus-dependent) live on incomparable scales — summing raw scores
  would just let whichever side has the bigger numbers dominate,
  regardless of `dense_weight`/`sparse_weight`.
- Reciprocal Rank Fusion (RRF): fuses by rank position instead of raw
  score, sidestepping the scale-comparability problem entirely — the
  standard approach systems like Elasticsearch's hybrid search use.
  `k` (default 60, the constant from the original RRF paper) dampens
  the influence of very low ranks.

Both return every chunk seen by *either* retriever (a chunk with no
BM25 term overlap still surfaces if its dense score is high, and vice
versa) — this is the "candidate pool" Phase 9's architecture doc
section 60 asks for, generated before final ranking/truncation.
"""

from dataclasses import dataclass


@dataclass
class FusedHit:
    chunk_id: str
    fused_score: float
    dense_score: float | None
    sparse_score: float | None


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return dict.fromkeys(scores, 1.0)
    return {chunk_id: (score - lo) / (hi - lo) for chunk_id, score in scores.items()}


def weighted_sum(
    dense: dict[str, float],
    sparse: dict[str, float],
    dense_weight: float,
    sparse_weight: float,
) -> list[FusedHit]:
    norm_dense = _normalize(dense)
    norm_sparse = _normalize(sparse)
    chunk_ids = set(dense) | set(sparse)
    hits = [
        FusedHit(
            chunk_id=chunk_id,
            fused_score=(
                dense_weight * norm_dense.get(chunk_id, 0.0)
                + sparse_weight * norm_sparse.get(chunk_id, 0.0)
            ),
            dense_score=dense.get(chunk_id),
            sparse_score=sparse.get(chunk_id),
        )
        for chunk_id in chunk_ids
    ]
    return sorted(hits, key=lambda hit: hit.fused_score, reverse=True)


def _ranks(scores: dict[str, float]) -> dict[str, int]:
    ordered = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    return {chunk_id: rank for rank, chunk_id in enumerate(ordered, start=1)}


def reciprocal_rank_fusion(
    dense: dict[str, float], sparse: dict[str, float], k: int
) -> list[FusedHit]:
    dense_ranks = _ranks(dense)
    sparse_ranks = _ranks(sparse)
    chunk_ids = set(dense) | set(sparse)
    hits = [
        FusedHit(
            chunk_id=chunk_id,
            fused_score=(
                (1.0 / (k + dense_ranks[chunk_id]) if chunk_id in dense_ranks else 0.0)
                + (1.0 / (k + sparse_ranks[chunk_id]) if chunk_id in sparse_ranks else 0.0)
            ),
            dense_score=dense.get(chunk_id),
            sparse_score=sparse.get(chunk_id),
        )
        for chunk_id in chunk_ids
    ]
    return sorted(hits, key=lambda hit: hit.fused_score, reverse=True)
