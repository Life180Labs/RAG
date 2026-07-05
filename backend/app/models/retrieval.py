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

Phase 11 (query understanding, docs/02-architecture.md sections 51-55)
extends this same model again, opt-in via `query_understanding_enabled`
(default False — existing dense/hybrid behavior is unchanged when
unset). When enabled, `retrieval_worker.query_understanding` classifies
the query's `QueryIntent`, rewrites it, generates paraphrase variants,
and extracts a metadata filter — all persisted here for the frontend's
Query Inspector/Rewrite Viewer/Generated Queries panels.
`detected_metadata_filter` is kept separate from the caller-supplied
`metadata_filter` (Phase 9) because they have different provenance and
different precedence when merged (caller-supplied wins on key
conflicts) — collapsing them into one column would lose which one a
value came from.

Phase 12 (advanced retrieval, docs/02-architecture.md sections 62-63,
75, 103) adds four more opt-in flags, each independently toggleable and
each defaulting to off so Phase 9-11 behavior is unchanged when unset:
`expand_to_parent` (Parent-Child retrieval — search still happens on
whatever chunk actually matched, this only remaps the *returned*
identity to that chunk's parent when one exists), `use_mmr`/
`mmr_lambda` (Maximum Marginal Relevance diversification of the final
result list), `compress_context` (per-result sentence-level
compression, persisted on `RetrievalResult.compressed_text` rather than
mutating `chunk_text` so the original is always still inspectable).
`fusion_method` gains `RAG_FUSION`, which requires
`query_understanding_enabled=True` (see `CreateRetrievalRequest`) since
RAG Fusion's whole premise (docs/02-architecture.md section 103) is
fusing multiple query variants' ranked lists — with only one variant
it degenerates to plain RRF, which the existing `RRF` option already
covers more cheaply. Self-Query and Multi-Query retrieval, also listed
among this phase's task.md deliverables, are not reimplemented here —
they're the same capability Phase 11's `detected_metadata_filter` and
`generated_queries` already deliver (docs/02-architecture.md sections
54 and 65 describe the identical mechanism Phase 11's task.md section
51-55 already named "Query Expansion" and "Metadata Detection"), and
duplicating that logic under a second name would just be dead code.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RetrievalStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class QueryIntent(str, enum.Enum):
    FACT_LOOKUP = "fact_lookup"
    DEFINITION = "definition"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    MULTI_HOP_REASONING = "multi_hop_reasoning"
    NUMERICAL_QUERY = "numerical_query"
    CODE_QUESTION = "code_question"
    TABLE_LOOKUP = "table_lookup"
    POLICY_LOOKUP = "policy_lookup"
    CONVERSATIONAL_FOLLOWUP = "conversational_followup"


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
    RAG_FUSION = "rag_fusion"


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
    query_understanding_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    query_intent: Mapped[QueryIntent | None] = mapped_column(
        Enum(QueryIntent, name="query_intent"), nullable=True
    )
    intent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    rewritten_query_text: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    generated_queries: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    detected_metadata_filter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expand_to_parent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    use_mmr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mmr_lambda: Mapped[float | None] = mapped_column(Float, nullable=True)
    compress_context: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    compressed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
