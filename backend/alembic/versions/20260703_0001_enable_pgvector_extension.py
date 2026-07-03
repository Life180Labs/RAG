"""Enable pgvector extension.

Revision ID: 0001_enable_pgvector
Revises:
Create Date: 2026-07-03

This is the foundational migration for Phase 0. It enables the `vector`
extension used by every embedding table added in later phases
(docs/03-database.md section 4 — PgVector Design).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_enable_pgvector"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
