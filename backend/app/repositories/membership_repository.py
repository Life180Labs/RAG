"""Repositories for the three membership tables. They share an identical
shape (org/workspace/project + user + role), but stay separate classes —
one per table — rather than a single generic one, since each is scoped to
a different foreign key and the base repository already generalizes CRUD.
"""

import uuid

from sqlalchemy import select

from app.models.organization import OrganizationMember
from app.models.project import ProjectMember
from app.models.workspace import WorkspaceMember
from app.repositories.base import BaseRepository


class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    model = OrganizationMember

    async def get_membership(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMember | None:
        result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[OrganizationMember]:
        result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id
            )
        )
        return list(result.scalars().all())


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember

    async def get_membership(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


class ProjectMemberRepository(BaseRepository[ProjectMember]):
    model = ProjectMember

    async def get_membership(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectMember | None:
        result = await self.session.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
