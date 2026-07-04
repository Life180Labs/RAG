"""Add hybrid retrieval columns to retrievals/retrieval_results (Phase 10).

Revision ID: 0011_add_hybrid_retrieval
Revises: 0010_add_retrieval_tables
Create Date: 2026-07-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011_add_hybrid_retrieval"
down_revision: str | None = "0010_add_retrieval_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

retrieval_mode_enum = postgresql.ENUM("DENSE", "HYBRID", name="retrieval_mode", create_type=False)
fusion_method_enum = postgresql.ENUM(
    "WEIGHTED_SUM", "RRF", name="fusion_method", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    retrieval_mode_enum.create(bind, checkfirst=True)
    fusion_method_enum.create(bind, checkfirst=True)

    op.add_column(
        "retrievals",
        sa.Column(
            "retrieval_mode", retrieval_mode_enum, nullable=False, server_default="DENSE"
        ),
    )
    op.add_column("retrievals", sa.Column("fusion_method", fusion_method_enum, nullable=True))
    op.add_column("retrievals", sa.Column("dense_weight", sa.Float(), nullable=True))
    op.add_column("retrievals", sa.Column("sparse_weight", sa.Float(), nullable=True))
    op.add_column("retrievals", sa.Column("rrf_k", sa.Integer(), nullable=True))

    op.add_column("retrieval_results", sa.Column("dense_score", sa.Float(), nullable=True))
    op.add_column("retrieval_results", sa.Column("sparse_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("retrieval_results", "sparse_score")
    op.drop_column("retrieval_results", "dense_score")

    op.drop_column("retrievals", "rrf_k")
    op.drop_column("retrievals", "sparse_weight")
    op.drop_column("retrievals", "dense_weight")
    op.drop_column("retrievals", "fusion_method")
    op.drop_column("retrievals", "retrieval_mode")

    bind = op.get_bind()
    fusion_method_enum.drop(bind, checkfirst=True)
    retrieval_mode_enum.drop(bind, checkfirst=True)
