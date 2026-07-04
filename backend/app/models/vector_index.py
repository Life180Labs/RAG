"""Vector index models (docs/05-task.md Phase 8; docs/02-architecture.md
section 43 Vector Indexing).

Mirrors Phase 7's EmbeddingVersion pattern one level deeper: `VectorIndex`
is one built index — a specific provider applied to a specific embedding
version — `IndexVersion` is the audit trail of build/rebuild events for
that index (build duration, vector count, outcome), and `VectorMetadata`
holds arbitrary per-chunk key/value payload attached at index time so
retrieval (Phase 9) can filter results by metadata (heading, page,
language, or anything else callers attach) the same way Pinecone/Qdrant/
Chroma's native metadata filtering works.

Re-running "create index" for a (embedding_version, provider) pair that
already has one rebuilds it in place (same id, `version` bumped on
`VectorIndex`, a new `IndexVersion` row appended) — the same
regenerate-in-place pattern Phases 6-7 already established, for the
identical FK-safety reason.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VectorIndexStatus(str, enum.Enum):
    PENDING = "pending"
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"


class IndexVersionStatus(str, enum.Enum):
    READY = "ready"
    FAILED = "failed"


class VectorIndex(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vector_indexes"
    __table_args__ = (
        UniqueConstraint(
            "embedding_version_id", "provider", name="uq_vector_index_embedding_version_provider"
        ),
    )

    embedding_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("embedding_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Not a Postgres enum, same rationale as Chunk.strategy/EmbeddingVersion.provider.
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    index_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Collection/index name in the external store (or the Postgres index
    # name for pgvector) — unique per provider, generated deterministically
    # from embedding_version_id so rebuilds target the same namespace.
    namespace: Mapped[str] = mapped_column(String(200), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[VectorIndexStatus] = mapped_column(
        Enum(VectorIndexStatus, name="vector_index_status"),
        nullable=False,
        default=VectorIndexStatus.PENDING,
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    vector_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    build_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IndexVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "index_versions"

    vector_index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vector_indexes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[IndexVersionStatus] = mapped_column(
        Enum(IndexVersionStatus, name="index_version_status"), nullable=False
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    build_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class VectorMetadata(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "vector_metadata"
    __table_args__ = (
        UniqueConstraint("vector_index_id", "chunk_id", name="uq_vector_metadata_index_chunk"),
    )

    vector_index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vector_indexes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    metadata_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
