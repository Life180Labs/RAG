"""Add documents, document_versions, upload_sessions tables (Phase 4).

Revision ID: 0005_add_document_tables
Revises: 0004_add_repository_tables
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_add_document_tables"
down_revision: str | None = "0004_add_repository_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Both enums are new in this migration, so (unlike resource_status/member_role
# in 0003/0004) this migration owns their creation and drop.
document_status_enum = postgresql.ENUM(
    "UPLOADED",
    "VALIDATING",
    "VALIDATED",
    "PARSING",
    "OCR",
    "CLEANING",
    "CHUNKING",
    "EMBEDDING",
    "INDEXING",
    "READY",
    "FAILED_UPLOAD",
    "FAILED_VALIDATION",
    "FAILED_PARSE",
    "FAILED_OCR",
    "FAILED_CHUNK",
    "FAILED_EMBED",
    "FAILED_INDEX",
    name="document_status",
    create_type=False,
)
upload_session_status_enum = postgresql.ENUM(
    "PENDING", "COMPLETED", "FAILED", name="upload_session_status", create_type=False
)


def _timestamp_columns() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    bind = op.get_bind()
    document_status_enum.create(bind, checkfirst=True)
    upload_session_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("status", document_status_enum, nullable=False),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        *_timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_repository_id"), "documents", ["repository_id"])
    op.create_index(op.f("ix_documents_sha256_hash"), "documents", ["sha256_hash"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("status", document_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version", name="uq_document_version"),
    )
    op.create_index(
        op.f("ix_document_versions_document_id"), "document_versions", ["document_id"]
    )

    op.create_table(
        "upload_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("status", upload_session_status_enum, nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_upload_sessions_repository_id"), "upload_sessions", ["repository_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_upload_sessions_repository_id"), table_name="upload_sessions")
    op.drop_table("upload_sessions")

    op.drop_index(op.f("ix_document_versions_document_id"), table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index(op.f("ix_documents_sha256_hash"), table_name="documents")
    op.drop_index(op.f("ix_documents_repository_id"), table_name="documents")
    op.drop_table("documents")

    bind = op.get_bind()
    upload_session_status_enum.drop(bind, checkfirst=True)
    document_status_enum.drop(bind, checkfirst=True)
