import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.vector_index import IndexVersionStatus, VectorIndexStatus


class VectorIndexRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    embedding_version_id: uuid.UUID
    document_id: uuid.UUID
    provider: str
    index_type: str
    namespace: str
    dimensions: int
    version: int
    status: VectorIndexStatus
    status_message: str | None
    vector_count: int
    build_duration_ms: int | None
    created_at: datetime
    updated_at: datetime


class IndexVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vector_index_id: uuid.UUID
    version: int
    vector_count: int
    status: IndexVersionStatus
    status_message: str | None
    build_duration_ms: int | None


class CreateVectorIndexRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=20)
    index_type: str = Field(default="hnsw", min_length=1, max_length=20)
