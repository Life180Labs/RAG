"""Add retrievals and retrieval_results tables (Phase 9).

Revision ID: 0010_add_retrieval_tables
Revises: 0009_add_vector_index_tables
Create Date: 2026-07-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_add_retrieval_tables"
down_revision: str | None = "0009_add_vector_index_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

retrieval_status_enum = postgresql.ENUM(
    "PENDING", "COMPLETED", "FAILED", name="retrieval_status", create_type=False
)
similarity_metric_enum = postgresql.ENUM(
    "COSINE", "DOT", "EUCLIDEAN", name="similarity_metric", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    retrieval_status_enum.create(bind, checkfirst=True)
    similarity_metric_enum.create(bind, checkfirst=True)

    op.create_table(
        "retrievals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("vector_index_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("query_text", sa.String(length=2000), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("score_threshold", sa.Float(), nullable=True),
        sa.Column("similarity_metric", similarity_metric_enum, nullable=False),
        sa.Column("metadata_filter", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", retrieval_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("avg_similarity", sa.Float(), nullable=True),
        sa.Column("min_similarity", sa.Float(), nullable=True),
        sa.Column("max_similarity", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["vector_index_id"], ["vector_indexes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_retrievals_vector_index_id"), "retrievals", ["vector_index_id"])
    op.create_index(op.f("ix_retrievals_document_id"), "retrievals", ["document_id"])

    op.create_table(
        "retrieval_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("retrieval_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["retrieval_id"], ["retrievals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_retrieval_results_retrieval_id"), "retrieval_results", ["retrieval_id"])
    op.create_index(op.f("ix_retrieval_results_chunk_id"), "retrieval_results", ["chunk_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_retrieval_results_chunk_id"), table_name="retrieval_results")
    op.drop_index(op.f("ix_retrieval_results_retrieval_id"), table_name="retrieval_results")
    op.drop_table("retrieval_results")

    op.drop_index(op.f("ix_retrievals_document_id"), table_name="retrievals")
    op.drop_index(op.f("ix_retrievals_vector_index_id"), table_name="retrievals")
    op.drop_table("retrievals")

    bind = op.get_bind()
    similarity_metric_enum.drop(bind, checkfirst=True)
    retrieval_status_enum.drop(bind, checkfirst=True)
