"""Repository model — the container for documents, embeddings,
evaluations, and experiments (docs/01-project.md, docs/02-architecture.md
section 12). Scoped under a Project, one level below in the tenancy
hierarchy (Organization -> Workspace -> Project -> Repository).

Statistics columns (document_count, ...) are maintained by future
document/chunk/embedding phases — they start at zero here since no
document pipeline exists yet. Settings columns store the *identifier* of
a default strategy/model/etc.; the engines those identifiers select are
implemented in later phases too.
"""

import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.membership import MemberRole, ResourceStatus


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("project_id", "slug", name="uq_repository_project_slug"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus, name="resource_status"), nullable=False, default=ResourceStatus.ACTIVE
    )

    # Settings — identifiers only; the engines they select are future phases.
    default_chunk_strategy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_retriever: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_reranker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Statistics — incremented by the document/chunk/embedding/retrieval
    # phases once they exist; zero is the correct value until then.
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    retrieval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RepositoryMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repository_members"
    __table_args__ = (UniqueConstraint("repository_id", "user_id", name="uq_repository_member"),)

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole, name="member_role"), nullable=False)
