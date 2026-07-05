"""Add prompt_templates/prompts tables (Phase 14).

Revision ID: 0015_add_prompt_tables
Revises: 0014_add_reranking
Create Date: 2026-07-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015_add_prompt_tables"
down_revision: str | None = "0014_add_reranking"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

prompt_status_enum = postgresql.ENUM(
    "PENDING", "COMPLETED", "FAILED", name="prompt_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    prompt_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("formatting_instructions", sa.Text(), nullable=True),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "repository_id", "name", "version", name="uq_prompt_template_repository_name_version"
        ),
    )
    op.create_index(
        op.f("ix_prompt_templates_repository_id"), "prompt_templates", ["repository_id"]
    )

    op.create_table(
        "prompts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("retrieval_id", sa.UUID(), nullable=False),
        sa.Column("prompt_template_id", sa.UUID(), nullable=True),
        sa.Column("model_context_window", sa.Integer(), nullable=False),
        sa.Column("system_prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("conversation_tokens", sa.Integer(), nullable=False),
        sa.Column("context_tokens", sa.Integer(), nullable=False),
        sa.Column("query_tokens", sa.Integer(), nullable=False),
        sa.Column("response_budget_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("rendered_system_prompt", sa.Text(), nullable=True),
        sa.Column("rendered_context", sa.Text(), nullable=True),
        sa.Column("rendered_prompt", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", prompt_status_enum, nullable=False),
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
        sa.ForeignKeyConstraint(["retrieval_id"], ["retrievals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["prompt_template_id"], ["prompt_templates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prompts_retrieval_id"), "prompts", ["retrieval_id"])
    op.create_index(op.f("ix_prompts_prompt_template_id"), "prompts", ["prompt_template_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_prompts_prompt_template_id"), table_name="prompts")
    op.drop_index(op.f("ix_prompts_retrieval_id"), table_name="prompts")
    op.drop_table("prompts")

    op.drop_index(op.f("ix_prompt_templates_repository_id"), table_name="prompt_templates")
    op.drop_table("prompt_templates")

    bind = op.get_bind()
    prompt_status_enum.drop(bind, checkfirst=True)
