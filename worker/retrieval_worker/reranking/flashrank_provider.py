"""FlashRank reranking (docs/05-task.md Phase 13).

A separate, even lighter-weight local ONNX cross-encoder library than
`fastembed` (default model `ms-marco-TinyBERT-L-2-v2`, ~3MB) — listed
as its own required model in task.md rather than just another
`fastembed`-backed option, so it gets its own small dependency instead
of being folded into `reranking.local`.
"""

from functools import lru_cache

from flashrank import Ranker, RerankRequest

from retrieval_worker.reranking.base import RerankHit, RerankProvider

DEFAULT_MODEL = "ms-marco-TinyBERT-L-2-v2"
_CACHE_DIR = "/tmp/flashrank_cache"


@lru_cache(maxsize=1)
def _load_ranker(model_name: str) -> Ranker:
    return Ranker(model_name=model_name, cache_dir=_CACHE_DIR)


class FlashRankProvider(RerankProvider):
    provider_name = "flashrank"

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[RerankHit]:
        if not candidates:
            return []
        ranker = _load_ranker(self.model_name)
        passages = [{"id": chunk_id, "text": text} for chunk_id, text in candidates]
        results = ranker.rerank(RerankRequest(query=query, passages=passages))
        hits = [
            RerankHit(chunk_id=result["id"], score=float(result["score"])) for result in results
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)
