"""Embedding models (docs/05-task.md Phase 7; docs/02-architecture.md
sections 40-42).

Mirrors Phase 6's DocumentChunkSet/Chunk pattern: `EmbeddingVersion` is
one embedding run — a specific provider+model applied to a specific
chunk set — and `Embedding` holds the individual per-chunk vectors.
Multiple embedding versions can coexist per chunk set (one per model
actually tried), which is what makes "Compare Models" possible;
re-running the *same* provider+model replaces its version in place
(`uq_embedding_version_chunk_set_provider_model`) and bumps `version`,
mirroring how chunk regeneration reuses its chunk_set id rather than
accumulating duplicates.

pgvector requires a fixed dimension per column. Models in this phase
range from 384 (bge-small) to 1536 (OpenAI text-embedding-3-small)
dimensions, so `embedding` is declared as `vector(EMBEDDING_DIM_MAX)`
and smaller vectors are zero-padded on write; the true dimensionality
is recorded on `EmbeddingVersion.dimensions`. Zero-padding does not
corrupt similarity search *within* one model's vectors (both sides carry
the same trailing zeros), but comparing raw vectors *across* differently
padded dimensions is meaningless — retrieval (Phase 9) must always
filter to a single embedding_version before running ANN search.
"""

import enum
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

EMBEDDING_DIM_MAX = 1536


class EmbeddingVersionStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class EmbeddingStatus(str, enum.Enum):
    READY = "ready"
    FAILED = "failed"


class EmbeddingVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "embedding_versions"
    __table_args__ = (
        UniqueConstraint(
            "chunk_set_id",
            "provider",
            "model",
            name="uq_embedding_version_chunk_set_provider_model",
        ),
    )

    chunk_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunk_sets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Not a Postgres enum, same rationale as Chunk.strategy: new providers
    # are expected over time and a varchar avoids an ALTER TYPE migration
    # for each addition.
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[EmbeddingVersionStatus] = mapped_column(
        Enum(EmbeddingVersionStatus, name="embedding_version_status"),
        nullable=False,
        default=EmbeddingVersionStatus.PENDING,
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Embedding(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("embedding_version_id", "chunk_id", name="uq_embedding_version_chunk"),
    )

    embedding_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("embedding_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM_MAX), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EmbeddingStatus] = mapped_column(
        Enum(EmbeddingStatus, name="embedding_status"),
        nullable=False,
        default=EmbeddingStatus.READY,
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
