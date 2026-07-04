"""Chunk models (docs/05-task.md Phase 6; docs/02-architecture.md
sections 31-39).

A `DocumentChunkSet` is one chunking run — a specific strategy applied to
a specific document version. Multiple sets can coexist per document
(one per strategy actually tried), which is what makes "Compare
Chunkers" possible; re-running the *same* strategy replaces its set
(`uq_chunk_set_document_strategy`) rather than accumulating duplicates.

Chunk metadata (docs/02-architecture.md section 38) is stored as columns
directly on `Chunk` rather than a separate `chunk_metadata` table — it's
a strict 1:1 relationship with no independent lifecycle, so a join table
would only add overhead. "Section" from that list is represented by
`heading` (the nearest enclosing heading's text); there's no separate
outline-numbering system.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChunkSetStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class ChunkStatus(str, enum.Enum):
    READY = "ready"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentChunkSet(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_chunk_sets"
    __table_args__ = (
        UniqueConstraint("document_id", "strategy", name="uq_chunk_set_document_strategy"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Not a Postgres enum: new chunker strategies are expected to be added
    # over time (docs/05-task.md Phase 6 already lists 11), and a varchar
    # avoids an `ALTER TYPE ... ADD VALUE` migration for every addition —
    # unlike `status` below, which is a small, stable state machine.
    strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[ChunkSetStatus] = mapped_column(
        Enum(ChunkSetStatus, name="chunk_set_status"),
        nullable=False,
        default=ChunkSetStatus.PENDING,
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Chunk(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("chunk_set_id", "chunk_index", name="uq_chunk_set_index"),)

    chunk_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunk_sets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[ChunkStatus] = mapped_column(
        Enum(ChunkStatus, name="chunk_status"), nullable=False, default=ChunkStatus.READY
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Populated by the future embedding phase (Phase 7) — null until then,
    # matching how Document.language/.page_count were added in Phase 4 and
    # only populated once Phase 5 existed.
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
