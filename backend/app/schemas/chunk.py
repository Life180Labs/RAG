import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.chunk import ChunkSetStatus, ChunkStatus


class ChunkSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version: int
    strategy: str
    config: dict
    status: ChunkSetStatus
    status_message: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_set_id: uuid.UUID
    parent_chunk_id: uuid.UUID | None
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    token_count: int
    page: int | None
    heading: str | None
    language: str | None
    status: ChunkStatus
    status_message: str | None
    embedding_model: str | None


class GenerateChunksRequest(BaseModel):
    strategy: str = Field(..., min_length=1, max_length=20)
    config: dict | None = None


class ChunkSetComparison(BaseModel):
    strategy_a: ChunkSetRead
    chunks_a: list[ChunkRead]
    strategy_b: ChunkSetRead
    chunks_b: list[ChunkRead]
