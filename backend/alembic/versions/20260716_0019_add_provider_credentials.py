"""Add provider_credentials table (per-organization provider API keys).

Revision ID: 0019_add_provider_credentials
Revises: 0018_add_semantic_cache_entries
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019_add_provider_credentials"
down_revision: str | None = "0018_add_semantic_cache_entries"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("encrypted_key", sa.Text(), nullable=False),
        sa.Column("last_four", sa.String(length=4), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "provider", name="uq_provider_credential_org_provider"
        ),
    )
    op.create_index(
        op.f("ix_provider_credentials_organization_id"),
        "provider_credentials",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_provider_credentials_organization_id"), table_name="provider_credentials"
    )
    op.drop_table("provider_credentials")
