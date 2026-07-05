"""Add query understanding columns to retrievals (Phase 11).

Revision ID: 0012_query_understanding
Revises: 0011_add_hybrid_retrieval
Create Date: 2026-07-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012_query_understanding"
down_revision: str | None = "0011_add_hybrid_retrieval"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

query_intent_enum = postgresql.ENUM(
    "FACT_LOOKUP",
    "DEFINITION",
    "SUMMARIZATION",
    "COMPARISON",
    "MULTI_HOP_REASONING",
    "NUMERICAL_QUERY",
    "CODE_QUESTION",
    "TABLE_LOOKUP",
    "POLICY_LOOKUP",
    "CONVERSATIONAL_FOLLOWUP",
    name="query_intent",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    query_intent_enum.create(bind, checkfirst=True)

    op.add_column(
        "retrievals",
        sa.Column(
            "query_understanding_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("retrievals", sa.Column("query_intent", query_intent_enum, nullable=True))
    op.add_column("retrievals", sa.Column("intent_confidence", sa.Float(), nullable=True))
    op.add_column(
        "retrievals", sa.Column("rewritten_query_text", sa.String(length=2000), nullable=True)
    )
    op.add_column(
        "retrievals", sa.Column("generated_queries", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "retrievals", sa.Column("detected_metadata_filter", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("retrievals", "detected_metadata_filter")
    op.drop_column("retrievals", "generated_queries")
    op.drop_column("retrievals", "rewritten_query_text")
    op.drop_column("retrievals", "intent_confidence")
    op.drop_column("retrievals", "query_intent")
    op.drop_column("retrievals", "query_understanding_enabled")

    bind = op.get_bind()
    query_intent_enum.drop(bind, checkfirst=True)
