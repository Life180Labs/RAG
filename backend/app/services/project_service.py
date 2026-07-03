"""Project business logic.

Creating a project always makes the creator its OWNER at the project
level too, mirroring WorkspaceService (see docs/03-database.md section 6).
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import ConflictError
from app.models.audit_log import AuditLog
from app.models.membership import MemberRole, ResourceStatus
from app.models.project import Project, ProjectMember
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.membership_repository import ProjectMemberRepository
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        member_repository: ProjectMemberRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.projects = project_repository
        self.members = member_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def create(
        self, *, workspace_id: uuid.UUID, creator_id: uuid.UUID, name: str, slug: str
    ) -> Project:
        existing = await self.projects.get_by_slug_in_workspace(workspace_id, slug)
        if existing is not None:
            raise ConflictError(
                "A project with this slug already exists in the workspace.", code="SLUG_TAKEN"
            )

        project = Project(
            workspace_id=workspace_id,
            name=name,
            slug=slug,
            status=ResourceStatus.ACTIVE,
            owner_id=creator_id,
            created_by=creator_id,
            updated_by=creator_id,
        )
        await self.projects.add(project)

        await self.members.add(
            ProjectMember(project_id=project.id, user_id=creator_id, role=MemberRole.OWNER)
        )

        await self._record_audit(
            user_id=creator_id, action="project.create", resource=str(project.id)
        )
        return project

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[Project]:
        return await self.projects.list_by_workspace(workspace_id)

    async def update(self, project: Project, *, name: str, actor_id: uuid.UUID) -> Project:
        project.name = name
        project.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="project.update", resource=str(project.id)
        )
        return project

    async def archive(self, project: Project, *, actor_id: uuid.UUID) -> Project:
        project.status = ResourceStatus.ARCHIVED
        project.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="project.archive", resource=str(project.id)
        )
        return project

    async def restore(self, project: Project, *, actor_id: uuid.UUID) -> Project:
        project.status = ResourceStatus.ACTIVE
        project.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="project.restore", resource=str(project.id)
        )
        return project

    async def soft_delete(self, project: Project, *, actor_id: uuid.UUID) -> None:
        project.deleted_at = datetime.now(UTC)
        project.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="project.delete", resource=str(project.id)
        )
