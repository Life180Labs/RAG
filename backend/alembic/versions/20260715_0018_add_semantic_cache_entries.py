"""Add semantic cache table (Phase 17).

Revision ID: 0018_add_semantic_cache_entries
Revises: 0017_add_conversation_tables
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "0018_add_semantic_cache_entries"
down_revision: str | None = "0017_add_conversation_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

EMBEDDING_DIM_MAX = 1536


def upgrade() -> None:
    op.create_table(
        "semantic_cache_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("vector_index_id", sa.UUID(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_embedding", Vector(EMBEDDING_DIM_MAX), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vector_index_id"], ["vector_indexes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_semantic_cache_entries_repository_id"),
        "semantic_cache_entries",
        ["repository_id"],
    )
    op.create_index(
        op.f("ix_semantic_cache_entries_vector_index_id"),
        "semantic_cache_entries",
        ["vector_index_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_semantic_cache_entries_vector_index_id"), table_name="semantic_cache_entries"
    )
    op.drop_index(
        op.f("ix_semantic_cache_entries_repository_id"), table_name="semantic_cache_entries"
    )
    op.drop_table("semantic_cache_entries")
