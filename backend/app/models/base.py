"""Declarative base and shared mixins.

Every table in the platform must include a UUID primary key, created_at,
updated_at, and (where applicable) audit and soft-delete fields, per
docs/06-rule.md Database Rules.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # `onupdate` is a Python callable (not `func.now()`) so SQLAlchemy knows
    # the new value immediately at flush time. A server-side onupdate would
    # mark the attribute expired, requiring a lazy re-SELECT to learn it —
    # which raises MissingGreenlet under asyncio the moment anything (e.g.
    # Pydantic's `model_validate`) reads it outside the flush's greenlet.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditMixin:
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
