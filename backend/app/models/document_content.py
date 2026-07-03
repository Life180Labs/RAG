"""Parsed document content (docs/05-task.md Phase 5; structure preserved
per docs/02-architecture.md section 30 — parsers never flatten titles,
headings, lists, tables, and code blocks into plain text).

One row per document, representing the parse of its *current* version —
re-parsing (e.g. after a new version is uploaded) overwrites this row
rather than accumulating history, since only the current version's
content ever feeds later phases (chunking/embedding).
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentContent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "document_content"
    __table_args__ = (UniqueConstraint("document_id", name="uq_document_content_document"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Ordered list of typed blocks: [{"type": "heading"|"paragraph"|"list"|
    # "table"|"code"|"image", "text": ..., "level": int|None, "page": int|None}, ...]
    structured_content: Mapped[list] = mapped_column(JSONB, nullable=False)

    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reading_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parser_used: Mapped[str] = mapped_column(String(50), nullable=False)
    ocr_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
