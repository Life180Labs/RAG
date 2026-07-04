"""Add vector_indexes, index_versions, and vector_metadata tables (Phase 8).

Revision ID: 0009_add_vector_index_tables
Revises: 0008_add_embedding_tables
Create Date: 2026-07-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009_add_vector_index_tables"
down_revision: str | None = "0008_add_embedding_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

vector_index_status_enum = postgresql.ENUM(
    "PENDING", "BUILDING", "READY", "FAILED", name="vector_index_status", create_type=False
)
index_version_status_enum = postgresql.ENUM(
    "READY", "FAILED", name="index_version_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    vector_index_status_enum.create(bind, checkfirst=True)
    index_version_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "vector_indexes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("embedding_version_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("index_type", sa.String(length=20), nullable=False),
        sa.Column("namespace", sa.String(length=200), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", vector_index_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("vector_count", sa.Integer(), nullable=False),
        sa.Column("build_duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["embedding_version_id"], ["embedding_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "embedding_version_id", "provider",
            name="uq_vector_index_embedding_version_provider",
        ),
    )
    op.create_index(
        op.f("ix_vector_indexes_embedding_version_id"), "vector_indexes", ["embedding_version_id"]
    )
    op.create_index(op.f("ix_vector_indexes_document_id"), "vector_indexes", ["document_id"])

    op.create_table(
        "index_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("vector_index_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("vector_count", sa.Integer(), nullable=False),
        sa.Column("status", index_version_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("build_duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["vector_index_id"], ["vector_indexes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_index_versions_vector_index_id"), "index_versions", ["vector_index_id"]
    )

    op.create_table(
        "vector_metadata",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("vector_index_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("metadata_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["vector_index_id"], ["vector_indexes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "vector_index_id", "chunk_id", name="uq_vector_metadata_index_chunk"
        ),
    )
    op.create_index(
        op.f("ix_vector_metadata_vector_index_id"), "vector_metadata", ["vector_index_id"]
    )
    op.create_index(op.f("ix_vector_metadata_chunk_id"), "vector_metadata", ["chunk_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_vector_metadata_chunk_id"), table_name="vector_metadata")
    op.drop_index(op.f("ix_vector_metadata_vector_index_id"), table_name="vector_metadata")
    op.drop_table("vector_metadata")

    op.drop_index(op.f("ix_index_versions_vector_index_id"), table_name="index_versions")
    op.drop_table("index_versions")

    op.drop_index(op.f("ix_vector_indexes_document_id"), table_name="vector_indexes")
    op.drop_index(op.f("ix_vector_indexes_embedding_version_id"), table_name="vector_indexes")
    op.drop_table("vector_indexes")

    bind = op.get_bind()
    index_version_status_enum.drop(bind, checkfirst=True)
    vector_index_status_enum.drop(bind, checkfirst=True)
