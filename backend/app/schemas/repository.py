import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.membership import ResourceStatus
from app.schemas.validators import validate_name, validate_slug


class RepositoryCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None

    _validate_name = field_validator("name")(validate_name)
    _validate_slug = field_validator("slug")(validate_slug)


class RepositoryUpdate(BaseModel):
    name: str
    description: str | None = None

    _validate_name = field_validator("name")(validate_name)


class RepositorySettingsUpdate(BaseModel):
    default_chunk_strategy: str | None = None
    default_embedding_model: str | None = None
    default_retriever: str | None = None
    default_reranker: str | None = None
    default_prompt_version: str | None = None


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    status: ResourceStatus
    default_chunk_strategy: str | None
    default_embedding_model: str | None
    default_retriever: str | None
    default_reranker: str | None
    default_prompt_version: str | None
    document_count: int
    chunk_count: int
    embedding_count: int
    storage_used_bytes: int
    retrieval_count: int
    created_at: datetime
    updated_at: datetime


class RepositoryActivityEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action: str
    result: str
    created_at: datetime
