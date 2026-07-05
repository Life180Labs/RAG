"""Add advanced retrieval columns for parent-child/MMR/RAG-fusion/
compression (Phase 12).

Revision ID: 0013_advanced_retrieval
Revises: 0012_query_understanding
Create Date: 2026-07-10

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_advanced_retrieval"
down_revision: str | None = "0012_query_understanding"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE fusion_method ADD VALUE IF NOT EXISTS 'RAG_FUSION'")

    op.add_column(
        "retrievals",
        sa.Column("expand_to_parent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "retrievals", sa.Column("use_mmr", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("retrievals", sa.Column("mmr_lambda", sa.Float(), nullable=True))
    op.add_column(
        "retrievals",
        sa.Column("compress_context", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column("retrieval_results", sa.Column("compressed_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("retrieval_results", "compressed_text")

    op.drop_column("retrievals", "compress_context")
    op.drop_column("retrievals", "mmr_lambda")
    op.drop_column("retrievals", "use_mmr")
    op.drop_column("retrievals", "expand_to_parent")

    # Postgres has no `ALTER TYPE ... DROP VALUE` — removing an enum
    # label requires rebuilding the type, which isn't worth doing for a
    # downgrade path (the same tradeoff Phase 10/11's migrations would
    # face for their own enum additions if they ever needed reverting;
    # this one just happens to be the first to actually hit it). Any row
    # already using 'RAG_FUSION' would need to be migrated off it first
    # regardless, so a clean automatic downgrade isn't meaningfully
    # achievable here.