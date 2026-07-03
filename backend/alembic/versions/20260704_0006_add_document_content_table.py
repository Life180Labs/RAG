"""Add document_content table (Phase 5).

Revision ID: 0006_add_document_content_table
Revises: 0005_add_document_tables
Create Date: 2026-07-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_add_document_content_table"
down_revision: str | None = "0005_add_document_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_content",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("structured_content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=True),
        sa.Column("reading_time_seconds", sa.Integer(), nullable=True),
        sa.Column("parser_used", sa.String(length=50), nullable=False),
        sa.Column("ocr_used", sa.Boolean(), nullable=False),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_document_content_document"),
    )
    op.create_index(
        op.f("ix_document_content_document_id"), "document_content", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_content_document_id"), table_name="document_content")
    op.drop_table("document_content")
