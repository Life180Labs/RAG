"""Add repository and repository_members tables (Phase 3).

Revision ID: 0004_add_repository_tables
Revises: 0003_add_tenancy_tables
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_add_repository_tables"
down_revision: str | None = "0003_add_tenancy_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Both enum types already exist (created by 0003_add_tenancy_tables) —
# create_type=False here just prevents CREATE TABLE from also trying to
# create them. Ownership (and DROP TYPE on downgrade) stays with 0003.
resource_status_enum = postgresql.ENUM(
    "ACTIVE", "ARCHIVED", name="resource_status", create_type=False
)
member_role_enum = postgresql.ENUM(
    "OWNER", "ADMIN", "DEVELOPER", "VIEWER", name="member_role", create_type=False
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
    op.create_table(
        "repositories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", resource_status_enum, nullable=False),
        sa.Column("default_chunk_strategy", sa.String(length=100), nullable=True),
        sa.Column("default_embedding_model", sa.String(length=100), nullable=True),
        sa.Column("default_retriever", sa.String(length=100), nullable=True),
        sa.Column("default_reranker", sa.String(length=100), nullable=True),
        sa.Column("default_prompt_version", sa.String(length=100), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("embedding_count", sa.Integer(), nullable=False),
        sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False),
        sa.Column("retrieval_count", sa.Integer(), nullable=False),
        *_timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "slug", name="uq_repository_project_slug"),
    )
    op.create_index(op.f("ix_repositories_project_id"), "repositories", ["project_id"])

    op.create_table(
        "repository_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", member_role_enum, nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "user_id", name="uq_repository_member"),
    )
    op.create_index(
        op.f("ix_repository_members_repository_id"), "repository_members", ["repository_id"]
    )
    op.create_index(op.f("ix_repository_members_user_id"), "repository_members", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_repository_members_user_id"), table_name="repository_members")
    op.drop_index(
        op.f("ix_repository_members_repository_id"), table_name="repository_members"
    )
    op.drop_table("repository_members")

    op.drop_index(op.f("ix_repositories_project_id"), table_name="repositories")
    op.drop_table("repositories")
