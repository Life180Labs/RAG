"""Add multi-tenant hierarchy: organizations, workspaces, projects,
membership tables, and invitations (Phase 2).

Revision ID: 0003_add_tenancy_tables
Revises: 0002_add_auth_tables
Create Date: 2026-07-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_add_tenancy_tables"
down_revision: str | None = "0002_add_auth_tables"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# create_type=False: types are created/dropped explicitly below (see
# 0002_add_auth_tables for why — CREATE TABLE would otherwise also try to
# create them and fail with DuplicateObjectError).
resource_status_enum = postgresql.ENUM(
    "ACTIVE", "ARCHIVED", name="resource_status", create_type=False
)
member_role_enum = postgresql.ENUM(
    "OWNER", "ADMIN", "DEVELOPER", "VIEWER", name="member_role", create_type=False
)
invitation_status_enum = postgresql.ENUM(
    "PENDING", "ACCEPTED", "REJECTED", "EXPIRED", name="invitation_status", create_type=False
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
    resource_status_enum.create(bind, checkfirst=True)
    member_role_enum.create(bind, checkfirst=True)
    invitation_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", resource_status_enum, nullable=False),
        *_timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.create_table(
        "organization_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", member_role_enum, nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
    )
    op.create_index(
        op.f("ix_organization_members_organization_id"),
        "organization_members",
        ["organization_id"],
    )
    op.create_index(op.f("ix_organization_members_user_id"), "organization_members", ["user_id"])

    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", resource_status_enum, nullable=False),
        *_timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
    )
    op.create_index(op.f("ix_workspaces_organization_id"), "workspaces", ["organization_id"])

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", member_role_enum, nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index(
        op.f("ix_workspace_members_workspace_id"), "workspace_members", ["workspace_id"]
    )
    op.create_index(op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("status", resource_status_enum, nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=True),
        *_timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_project_workspace_slug"),
    )
    op.create_index(op.f("ix_projects_workspace_id"), "projects", ["workspace_id"])

    op.create_table(
        "project_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", member_role_enum, nullable=False),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )
    op.create_index(op.f("ix_project_members_project_id"), "project_members", ["project_id"])
    op.create_index(op.f("ix_project_members_user_id"), "project_members", ["user_id"])

    op.create_table(
        "invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", member_role_enum, nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("status", invitation_status_enum, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamp_columns(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_invitations_organization_id"), "invitations", ["organization_id"])
    op.create_index(op.f("ix_invitations_email"), "invitations", ["email"])


def downgrade() -> None:
    op.drop_index(op.f("ix_invitations_email"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_organization_id"), table_name="invitations")
    op.drop_table("invitations")

    op.drop_index(op.f("ix_project_members_user_id"), table_name="project_members")
    op.drop_index(op.f("ix_project_members_project_id"), table_name="project_members")
    op.drop_table("project_members")

    op.drop_index(op.f("ix_projects_workspace_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_workspace_members_user_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_workspace_id"), table_name="workspace_members")
    op.drop_table("workspace_members")

    op.drop_index(op.f("ix_workspaces_organization_id"), table_name="workspaces")
    op.drop_table("workspaces")

    op.drop_index(op.f("ix_organization_members_user_id"), table_name="organization_members")
    op.drop_index(
        op.f("ix_organization_members_organization_id"), table_name="organization_members"
    )
    op.drop_table("organization_members")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")

    bind = op.get_bind()
    invitation_status_enum.drop(bind, checkfirst=True)
    member_role_enum.drop(bind, checkfirst=True)
    resource_status_enum.drop(bind, checkfirst=True)
