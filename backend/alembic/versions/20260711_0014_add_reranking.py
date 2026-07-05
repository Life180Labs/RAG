"""Add reranking columns to retrievals/retrieval_results (Phase 13).

Revision ID: 0014_add_reranking
Revises: 0013_advanced_retrieval
Create Date: 2026-07-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014_add_reranking"
down_revision: str | None = "0013_advanced_retrieval"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

reranker_provider_enum = postgresql.ENUM(
    "CROSS_ENCODER", "BGE", "FLASHRANK", "COHERE", "JINA", name="reranker_provider"
)


def upgrade() -> None:
    bind = op.get_bind()
    reranker_provider_enum.create(bind, checkfirst=True)

    op.add_column(
        "retrievals",
        sa.Column("rerank_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "retrievals", sa.Column("reranker_provider", reranker_provider_enum, nullable=True)
    )
    op.add_column("retrieval_results", sa.Column("rerank_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("retrieval_results", "rerank_score")
    op.drop_column("retrievals", "reranker_provider")
    op.drop_column("retrievals", "rerank_enabled")

    bind = op.get_bind()
    reranker_provider_enum.drop(bind, checkfirst=True)
