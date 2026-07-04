import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.embedding import EmbeddingStatus, EmbeddingVersionStatus


class EmbeddingVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_set_id: uuid.UUID
    document_id: uuid.UUID
    provider: str
    model: str
    dimensions: int
    version: int
    status: EmbeddingVersionStatus
    status_message: str | None
    embedding_count: int
    total_tokens: int
    total_cost_usd: float | None
    avg_latency_ms: int | None
    created_at: datetime
    updated_at: datetime


class EmbeddingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    embedding_version_id: uuid.UUID
    chunk_id: uuid.UUID
    token_count: int
    cost_usd: float | None
    latency_ms: int
    status: EmbeddingStatus
    status_message: str | None


class GenerateEmbeddingsRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=20)
    model: str | None = Field(default=None, max_length=100)


class EmbeddingVersionComparison(BaseModel):
    version_a: EmbeddingVersionRead
    embeddings_a: list[EmbeddingRead]
    version_b: EmbeddingVersionRead
    embeddings_b: list[EmbeddingRead]
