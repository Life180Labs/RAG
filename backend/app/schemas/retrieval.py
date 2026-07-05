import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.retrieval import (
    FusionMethod,
    QueryIntent,
    RetrievalMode,
    RetrievalStatus,
    SimilarityMetric,
)

_DEFAULT_DENSE_WEIGHT = 0.7
_DEFAULT_SPARSE_WEIGHT = 0.3
_DEFAULT_RRF_K = 60
_DEFAULT_MMR_LAMBDA = 0.7


class RetrievalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vector_index_id: uuid.UUID
    document_id: uuid.UUID
    query_text: str
    top_k: int
    score_threshold: float | None
    similarity_metric: SimilarityMetric
    metadata_filter: dict | None
    retrieval_mode: RetrievalMode
    fusion_method: FusionMethod | None
    dense_weight: float | None
    sparse_weight: float | None
    rrf_k: int | None
    query_understanding_enabled: bool
    query_intent: QueryIntent | None
    intent_confidence: float | None
    rewritten_query_text: str | None
    generated_queries: list[str] | None
    detected_metadata_filter: dict | None
    expand_to_parent: bool
    use_mmr: bool
    mmr_lambda: float | None
    compress_context: bool
    status: RetrievalStatus
    status_message: str | None
    result_count: int
    avg_similarity: float | None
    min_similarity: float | None
    max_similarity: float | None
    latency_ms: int | None
    created_at: datetime
    updated_at: datetime


class RetrievalResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_id: uuid.UUID
    rank: int
    score: float
    dense_score: float | None
    sparse_score: float | None
    compressed_text: str | None
    chunk_text: str
    chunk_heading: str | None
    chunk_page: int | None


class CreateRetrievalRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=100)
    score_threshold: float | None = Field(default=None, ge=-1.0, le=1.0)
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    metadata_filter: dict | None = None
    retrieval_mode: RetrievalMode = RetrievalMode.DENSE
    fusion_method: FusionMethod | None = None
    dense_weight: float | None = Field(default=None, ge=0.0)
    sparse_weight: float | None = Field(default=None, ge=0.0)
    rrf_k: int | None = Field(default=None, ge=1)
    query_understanding_enabled: bool = False
    expand_to_parent: bool = False
    use_mmr: bool = False
    mmr_lambda: float | None = Field(default=None, ge=0.0, le=1.0)
    compress_context: bool = False

    @model_validator(mode="after")
    def _apply_hybrid_defaults(self) -> "CreateRetrievalRequest":
        if self.use_mmr and self.mmr_lambda is None:
            self.mmr_lambda = _DEFAULT_MMR_LAMBDA

        if self.fusion_method == FusionMethod.RAG_FUSION:
            if not self.query_understanding_enabled:
                raise ValueError(
                    "fusion_method 'rag_fusion' requires query_understanding_enabled=true — "
                    "RAG Fusion works by fusing multiple query variants' ranked lists, which "
                    "requires query understanding to generate those variants."
                )
            self.rrf_k = self.rrf_k if self.rrf_k is not None else _DEFAULT_RRF_K
            return self

        if self.retrieval_mode != RetrievalMode.HYBRID:
            return self

        if self.fusion_method is None:
            self.fusion_method = FusionMethod.WEIGHTED_SUM

        if self.fusion_method == FusionMethod.WEIGHTED_SUM:
            dense_weight = (
                self.dense_weight if self.dense_weight is not None else _DEFAULT_DENSE_WEIGHT
            )
            sparse_weight = (
                self.sparse_weight if self.sparse_weight is not None else _DEFAULT_SPARSE_WEIGHT
            )
            total = dense_weight + sparse_weight
            if total <= 0:
                raise ValueError("dense_weight and sparse_weight cannot both be zero.")
            # Normalize so the two always sum to 1 — keeps the relative
            # weighting the caller intended (e.g. 2/1 stays 2:1) while
            # making the stored weights directly interpretable as a
            # split, per docs/02-architecture.md section 58's example.
            self.dense_weight = dense_weight / total
            self.sparse_weight = sparse_weight / total
        else:
            self.rrf_k = self.rrf_k if self.rrf_k is not None else _DEFAULT_RRF_K

        return self
