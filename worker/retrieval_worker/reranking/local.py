"""Local ONNX-backed cross-encoder reranking (docs/05-task.md Phase 13).

Runs entirely locally via `fastembed`'s `TextCrossEncoder` — the same
ONNX-runtime approach Phase 7's local embedding providers use, no torch
dependency, no API key. `"cross_encoder"` is the lightweight
general-purpose default (`Xenova/ms-marco-MiniLM-L-6-v2`, ~80MB,
pre-cached at Docker build time — see worker/Dockerfile.dev);
`"bge"` is BAAI's larger, higher-quality reranker model (~1GB,
downloads on first use rather than being pre-cached, the same
build-time-size tradeoff Phase 7 documented for its non-default local
embedding models).
"""

from functools import lru_cache

from fastembed.rerank.cross_encoder import TextCrossEncoder

from retrieval_worker.reranking.base import RerankHit, RerankProvider

LOCAL_MODEL_NAMES: dict[str, str] = {
    "cross_encoder": "Xenova/ms-marco-MiniLM-L-6-v2",
    "bge": "BAAI/bge-reranker-base",
}


@lru_cache(maxsize=len(LOCAL_MODEL_NAMES))
def _load_model(model_name: str) -> TextCrossEncoder:
    return TextCrossEncoder(model_name=model_name)


class LocalRerankProvider(RerankProvider):
    def __init__(self, provider_name: str) -> None:
        if provider_name not in LOCAL_MODEL_NAMES:
            raise ValueError(f"Unknown local rerank provider '{provider_name}'.")
        self.provider_name = provider_name
        self.model_name = LOCAL_MODEL_NAMES[provider_name]

    def rerank(self, query: str, candidates: list[tuple[str, str]]) -> list[RerankHit]:
        if not candidates:
            return []
        model = _load_model(self.model_name)
        texts = [text for _, text in candidates]
        scores = list(model.rerank(query, texts))
        hits = [
            RerankHit(chunk_id=chunk_id, score=float(score))
            for (chunk_id, _text), score in zip(candidates, scores, strict=True)
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)
