"""Add conversation memory tables (Phase 16).

Revision ID: 0017_add_conversation_tables
Revises: 0016_add_llm_requests
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0017_add_conversation_tables"
down_revision: str | None = "0016_add_llm_requests"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

message_role_enum = postgresql.ENUM("USER", "ASSISTANT", name="message_role", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    message_role_enum.create(bind, checkfirst=True)

    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("vector_index_id", sa.UUID(), nullable=False),
        sa.Column("prompt_template_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vector_index_id"], ["vector_indexes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["prompt_template_id"], ["prompt_templates.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversations_repository_id"), "conversations", ["repository_id"])
    op.create_index(op.f("ix_conversations_document_id"), "conversations", ["document_id"])
    op.create_index(
        op.f("ix_conversations_vector_index_id"), "conversations", ["vector_index_id"]
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", message_role_enum, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("retrieval_id", sa.UUID(), nullable=True),
        sa.Column("prompt_id", sa.UUID(), nullable=True),
        sa.Column("llm_request_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["retrieval_id"], ["retrievals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["llm_request_id"], ["llm_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_messages_conversation_id"), "messages", ["conversation_id"])

    op.create_table(
        "conversation_summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("covers_message_count", sa.Integer(), nullable=False),
        sa.Column("covers_up_to_message_id", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["covers_up_to_message_id"], ["messages.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_conversation_summaries_conversation_id"),
        "conversation_summaries",
        ["conversation_id"],
    )

    op.create_table(
        "conversation_memory",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("custom_instructions", sa.Text(), nullable=True),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "repository_id", name="uq_conversation_memory_user_repository"
        ),
    )
    op.create_index(
        op.f("ix_conversation_memory_user_id"), "conversation_memory", ["user_id"]
    )
    op.create_index(
        op.f("ix_conversation_memory_repository_id"), "conversation_memory", ["repository_id"]
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_conversation_memory_repository_id"), table_name="conversation_memory"
    )
    op.drop_index(op.f("ix_conversation_memory_user_id"), table_name="conversation_memory")
    op.drop_table("conversation_memory")

    op.drop_index(
        op.f("ix_conversation_summaries_conversation_id"),
        table_name="conversation_summaries",
    )
    op.drop_table("conversation_summaries")

    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_conversations_vector_index_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_document_id"), table_name="conversations")
    op.drop_index(op.f("ix_conversations_repository_id"), table_name="conversations")
    op.drop_table("conversations")

    bind = op.get_bind()
    message_role_enum.drop(bind, checkfirst=True)
