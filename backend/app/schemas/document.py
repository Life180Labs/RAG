import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    sha256_hash: str
    status: DocumentStatus
    status_message: str | None
    current_version: int
    language: str | None
    page_count: int | None
    uploaded_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    filename: str
    size_bytes: int
    sha256_hash: str
    status: DocumentStatus
    created_at: datetime


class DownloadResponse(BaseModel):
    """Either `url` (presigned, direct-from-storage) or a note that the
    caller should hit the streaming download endpoint instead (local
    storage backend — see docs/03-database.md section on Document
    storage)."""

    url: str | None
    stream_via_backend: bool
