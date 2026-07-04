"""Add document_chunk_sets and chunks tables (Phase 6).

Revision ID: 0007_add_chunk_tables
Revises: 0006_add_document_content_table
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_add_chunk_tables"
down_revision: str | None = "0006_add_document_content_table"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

chunk_set_status_enum = postgresql.ENUM(
    "PENDING", "READY", "FAILED", name="chunk_set_status", create_type=False
)
chunk_status_enum = postgresql.ENUM(
    "READY", "FAILED", "SKIPPED", name="chunk_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    chunk_set_status_enum.create(bind, checkfirst=True)
    chunk_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "document_chunk_sets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(length=20), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", chunk_set_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "strategy", name="uq_chunk_set_document_strategy"
        ),
    )
    op.create_index(
        op.f("ix_document_chunk_sets_document_id"), "document_chunk_sets", ["document_id"]
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chunk_set_id", sa.UUID(), nullable=False),
        sa.Column("parent_chunk_id", sa.UUID(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("heading", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("status", chunk_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["chunk_set_id"], ["document_chunk_sets.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["parent_chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_set_id", "chunk_index", name="uq_chunk_set_index"),
    )
    op.create_index(op.f("ix_chunks_chunk_set_id"), "chunks", ["chunk_set_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_chunks_chunk_set_id"), table_name="chunks")
    op.drop_table("chunks")

    op.drop_index(op.f("ix_document_chunk_sets_document_id"), table_name="document_chunk_sets")
    op.drop_table("document_chunk_sets")

    bind = op.get_bind()
    chunk_status_enum.drop(bind, checkfirst=True)
    chunk_set_status_enum.drop(bind, checkfirst=True)
