import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.retrieval import RetrievalStatus, SimilarityMetric


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
    chunk_text: str
    chunk_heading: str | None
    chunk_page: int | None


class CreateRetrievalRequest(BaseModel):
    query_text: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=100)
    score_threshold: float | None = Field(default=None, ge=-1.0, le=1.0)
    similarity_metric: SimilarityMetric = SimilarityMetric.COSINE
    metadata_filter: dict | None = None
