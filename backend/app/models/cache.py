"""Semantic cache model (docs/05-task.md Phase 17; docs/02-architecture.md
section 99's "Semantic Cache": embed the incoming query, vector-search
past cached queries, and return the cached answer directly when
similarity clears a threshold instead of re-running the full RAG
pipeline.

Scoped to `vector_index_id` (same granularity as `Conversation`/
`Retrieval`) rather than being global — a cached answer for one index's
documents has no business being returned for a different index's query,
even if the query text happens to be similar. `query_embedding` reuses
the exact zero-padding convention `app/models/embedding.py` already
established (`Vector(EMBEDDING_DIM_MAX)`, true dimensionality tracked
separately) so the same pgvector column type and similarity operators
work unchanged; a lookup must still be scoped to entries whose embedding
came from the same embedding_version-equivalent model, which in practice
means scoping to `vector_index_id` (one embedding model per index).
"""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.embedding import EMBEDDING_DIM_MAX


class SemanticCacheEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "semantic_cache_entries"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    vector_index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vector_indexes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM_MAX), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
