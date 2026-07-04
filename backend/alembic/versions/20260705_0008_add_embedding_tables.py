"""Add embedding_versions and embeddings tables (Phase 7).

Revision ID: 0008_add_embedding_tables
Revises: 0007_add_chunk_tables
Create Date: 2026-07-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_add_embedding_tables"
down_revision: str | None = "0007_add_chunk_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

EMBEDDING_DIM_MAX = 1536

embedding_version_status_enum = postgresql.ENUM(
    "PENDING", "READY", "FAILED", name="embedding_version_status", create_type=False
)
embedding_status_enum = postgresql.ENUM(
    "READY", "FAILED", name="embedding_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    embedding_version_status_enum.create(bind, checkfirst=True)
    embedding_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "embedding_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chunk_set_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", embedding_version_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("embedding_count", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_set_id"], ["document_chunk_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "chunk_set_id", "provider", "model",
            name="uq_embedding_version_chunk_set_provider_model",
        ),
    )
    op.create_index(
        op.f("ix_embedding_versions_chunk_set_id"), "embedding_versions", ["chunk_set_id"]
    )
    op.create_index(
        op.f("ix_embedding_versions_document_id"), "embedding_versions", ["document_id"]
    )

    op.create_table(
        "embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("embedding_version_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM_MAX), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("status", embedding_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["embedding_version_id"], ["embedding_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "embedding_version_id", "chunk_id", name="uq_embedding_version_chunk"
        ),
    )
    op.create_index(
        op.f("ix_embeddings_embedding_version_id"), "embeddings", ["embedding_version_id"]
    )
    op.create_index(op.f("ix_embeddings_chunk_id"), "embeddings", ["chunk_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_embeddings_chunk_id"), table_name="embeddings")
    op.drop_index(op.f("ix_embeddings_embedding_version_id"), table_name="embeddings")
    op.drop_table("embeddings")

    op.drop_index(op.f("ix_embedding_versions_document_id"), table_name="embedding_versions")
    op.drop_index(op.f("ix_embedding_versions_chunk_set_id"), table_name="embedding_versions")
    op.drop_table("embedding_versions")

    bind = op.get_bind()
    embedding_status_enum.drop(bind, checkfirst=True)
    embedding_version_status_enum.drop(bind, checkfirst=True)
