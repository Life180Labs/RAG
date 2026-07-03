"""Workspace business logic.

Creating a workspace always makes the creator its OWNER at the workspace
level too — organization membership alone doesn't grant workspace access
in this phase (see docs/03-database.md section 6).
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import ConflictError
from app.models.audit_log import AuditLog
from app.models.membership import MemberRole, ResourceStatus
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.membership_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository


class WorkspaceService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        member_repository: WorkspaceMemberRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.workspaces = workspace_repository
        self.members = member_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def create(
        self, *, organization_id: uuid.UUID, creator_id: uuid.UUID, name: str, slug: str
    ) -> Workspace:
        existing = await self.workspaces.get_by_slug_in_organization(organization_id, slug)
        if existing is not None:
            raise ConflictError(
                "A workspace with this slug already exists in the organization.",
                code="SLUG_TAKEN",
            )

        workspace = Workspace(
            organization_id=organization_id,
            name=name,
            slug=slug,
            status=ResourceStatus.ACTIVE,
            created_by=creator_id,
            updated_by=creator_id,
        )
        await self.workspaces.add(workspace)

        await self.members.add(
            WorkspaceMember(workspace_id=workspace.id, user_id=creator_id, role=MemberRole.OWNER)
        )

        await self._record_audit(
            user_id=creator_id, action="workspace.create", resource=str(workspace.id)
        )
        return workspace

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[Workspace]:
        return await self.workspaces.list_by_organization(organization_id)

    async def update(self, workspace: Workspace, *, name: str, actor_id: uuid.UUID) -> Workspace:
        workspace.name = name
        workspace.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="workspace.update", resource=str(workspace.id)
        )
        return workspace

    async def archive(self, workspace: Workspace, *, actor_id: uuid.UUID) -> Workspace:
        workspace.status = ResourceStatus.ARCHIVED
        workspace.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="workspace.archive", resource=str(workspace.id)
        )
        return workspace

    async def restore(self, workspace: Workspace, *, actor_id: uuid.UUID) -> Workspace:
        workspace.status = ResourceStatus.ACTIVE
        workspace.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="workspace.restore", resource=str(workspace.id)
        )
        return workspace

    async def soft_delete(self, workspace: Workspace, *, actor_id: uuid.UUID) -> None:
        workspace.deleted_at = datetime.now(UTC)
        workspace.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="workspace.delete", resource=str(workspace.id)
        )
