"""Add llm_requests table (Phase 15).

Revision ID: 0016_add_llm_requests
Revises: 0015_add_prompt_tables
Create Date: 2026-07-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016_add_llm_requests"
down_revision: str | None = "0015_add_prompt_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

llm_request_status_enum = postgresql.ENUM(
    "PENDING", "COMPLETED", "FAILED", name="llm_request_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    llm_request_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "llm_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("prompt_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("routing_hint", sa.String(length=20), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("stream", sa.Boolean(), nullable=False),
        sa.Column("json_mode", sa.Boolean(), nullable=False),
        sa.Column("attempted_providers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", llm_request_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_requests_prompt_id"), "llm_requests", ["prompt_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_requests_prompt_id"), table_name="llm_requests")
    op.drop_table("llm_requests")

    bind = op.get_bind()
    llm_request_status_enum.drop(bind, checkfirst=True)
