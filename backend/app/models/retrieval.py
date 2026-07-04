"""Retrieval models (docs/05-task.md Phases 9-10; docs/02-architecture.md
sections 56 Dense Retrieval, 57 Sparse Retrieval, 58 Hybrid Search).

`Retrieval` is one query execution — always scoped to a single
`VectorIndex` (never a whole repository at once), per the constraint
`backend/app/models/embedding.py` already documents: pgvector's
zero-padded columns make cross-embedding-version vector comparison
meaningless, so retrieval always targets one embedding_version's index.
`RetrievalResult` holds the ranked candidate list for that execution,
mirroring `VectorMetadata`'s per-chunk-row shape.

Unlike VectorIndex/EmbeddingVersion (which are re-buildable in place),
a Retrieval is a point-in-time query execution — re-running the same
query text creates a new row rather than reusing one, since two
executions of "the same" query can legitimately return different
results (index rebuilt in between, non-deterministic ANN search). No
regenerate-reuses-id handling needed here.

Phase 10 (hybrid search) extends this same model rather than
introducing a parallel "HybridRetrieval" concept: `retrieval_mode`
distinguishes dense-only (Phase 9's original behavior, unchanged) from
hybrid (dense + BM25 sparse, fused). `dense_score`/`sparse_score` on
`RetrievalResult` are only populated for hybrid retrievals — for
dense-only ones, `score` alone (as it always did) is the dense
similarity. `Retrieval.score_threshold`/`top_k` continue to mean "on
the final score" — the fused score for hybrid, the dense similarity for
dense-only — so the "Threshold"/"Top-K" configuration in Phase 9's spec
needs no separate hybrid-only field.
"""

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RetrievalStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SimilarityMetric(str, enum.Enum):
    COSINE = "cosine"
    DOT = "dot"
    EUCLIDEAN = "euclidean"


class RetrievalMode(str, enum.Enum):
    DENSE = "dense"
    HYBRID = "hybrid"


class FusionMethod(str, enum.Enum):
    WEIGHTED_SUM = "weighted_sum"
    RRF = "rrf"


class Retrieval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "retrievals"

    vector_index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vector_indexes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    query_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    score_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity_metric: Mapped[SimilarityMetric] = mapped_column(
        Enum(SimilarityMetric, name="similarity_metric"),
        nullable=False,
        default=SimilarityMetric.COSINE,
    )
    metadata_filter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retrieval_mode: Mapped[RetrievalMode] = mapped_column(
        Enum(RetrievalMode, name="retrieval_mode"),
        nullable=False,
        default=RetrievalMode.DENSE,
    )
    fusion_method: Mapped[FusionMethod | None] = mapped_column(
        Enum(FusionMethod, name="fusion_method"), nullable=True
    )
    dense_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    sparse_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    rrf_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[RetrievalStatus] = mapped_column(
        Enum(RetrievalStatus, name="retrieval_status"),
        nullable=False,
        default=RetrievalStatus.PENDING,
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class RetrievalResult(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "retrieval_results"

    retrieval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrievals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    dense_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sparse_score: Mapped[float | None] = mapped_column(Float, nullable=True)
