import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.membership import MemberRole, ResourceStatus


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus, name="resource_status"), nullable=False, default=ResourceStatus.ACTIVE
    )


class WorkspaceMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[MemberRole] = mapped_column(Enum(MemberRole, name="member_role"), nullable=False)
