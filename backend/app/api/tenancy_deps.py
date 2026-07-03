"""Tenant-scoped RBAC dependencies for the Organization -> Workspace ->
Project hierarchy (docs/02-architecture.md section 121/127).

Each `require_*_role` factory both enforces tenant isolation (the
resource must exist and the caller must be a member of it — no query
ever succeeds by ID alone) and role sufficiency, returning the
membership row so services can log `membership.role` without a second
lookup. Membership at each level is explicit: creating a workspace
requires an organization role, but *managing* that workspace requires
workspace membership (auto-granted OWNER to its creator) — org
admins do not implicitly inherit access to every child workspace/project
in this phase. This is a deliberate MVP simplification, documented in
docs/03-database.md section 6, revisited if implicit inheritance proves
necessary.
"""

import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository, get_current_user, get_user_repository
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.membership import MemberRole, role_meets_minimum
from app.models.organization import OrganizationMember
from app.models.project import ProjectMember
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import (
    OrganizationMemberRepository,
    ProjectMemberRepository,
    WorkspaceMemberRepository,
)
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.invitation_service import InvitationService
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService


def get_organization_repository(db: AsyncSession = Depends(get_db)) -> OrganizationRepository:
    return OrganizationRepository(db)


def get_organization_member_repository(
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberRepository:
    return OrganizationMemberRepository(db)


def get_workspace_repository(db: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    return WorkspaceRepository(db)


def get_workspace_member_repository(
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMemberRepository:
    return WorkspaceMemberRepository(db)


def get_project_repository(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db)


def get_project_member_repository(db: AsyncSession = Depends(get_db)) -> ProjectMemberRepository:
    return ProjectMemberRepository(db)


def require_organization_role(minimum: MemberRole):
    """`Depends(require_organization_role(MemberRole.ADMIN))` on a route
    with an `organization_id` path parameter."""

    async def _dependency(
        organization_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        org_repo: OrganizationRepository = Depends(get_organization_repository),
        member_repo: OrganizationMemberRepository = Depends(get_organization_member_repository),
    ) -> OrganizationMember:
        organization = await org_repo.get_active_by_id(organization_id)
        if organization is None:
            raise NotFoundError("Organization not found.", code="ORGANIZATION_NOT_FOUND")

        membership = await member_repo.get_membership(organization_id, current_user.id)
        if membership is None:
            raise ForbiddenError("You are not a member of this organization.", code="NOT_A_MEMBER")
        if not role_meets_minimum(membership.role, minimum):
            raise ForbiddenError("Insufficient role for this action.", code="FORBIDDEN")
        return membership

    return _dependency


def require_workspace_role(minimum: MemberRole):
    """`Depends(require_workspace_role(MemberRole.ADMIN))` on a route with
    a `workspace_id` path parameter."""

    async def _dependency(
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
        member_repo: WorkspaceMemberRepository = Depends(get_workspace_member_repository),
    ) -> WorkspaceMember:
        workspace = await workspace_repo.get_active_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace not found.", code="WORKSPACE_NOT_FOUND")

        membership = await member_repo.get_membership(workspace_id, current_user.id)
        if membership is None:
            raise ForbiddenError("You are not a member of this workspace.", code="NOT_A_MEMBER")
        if not role_meets_minimum(membership.role, minimum):
            raise ForbiddenError("Insufficient role for this action.", code="FORBIDDEN")
        return membership

    return _dependency


def require_project_role(minimum: MemberRole):
    """`Depends(require_project_role(MemberRole.ADMIN))` on a route with a
    `project_id` path parameter."""

    async def _dependency(
        project_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        project_repo: ProjectRepository = Depends(get_project_repository),
        member_repo: ProjectMemberRepository = Depends(get_project_member_repository),
    ) -> ProjectMember:
        project = await project_repo.get_active_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        membership = await member_repo.get_membership(project_id, current_user.id)
        if membership is None:
            raise ForbiddenError("You are not a member of this project.", code="NOT_A_MEMBER")
        if not role_meets_minimum(membership.role, minimum):
            raise ForbiddenError("Insufficient role for this action.", code="FORBIDDEN")
        return membership

    return _dependency


def get_organization_service(
    organization_repository: OrganizationRepository = Depends(get_organization_repository),
    member_repository: OrganizationMemberRepository = Depends(get_organization_member_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> OrganizationService:
    return OrganizationService(organization_repository, member_repository, audit_log_repository)


def get_workspace_service(
    workspace_repository: WorkspaceRepository = Depends(get_workspace_repository),
    member_repository: WorkspaceMemberRepository = Depends(get_workspace_member_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> WorkspaceService:
    return WorkspaceService(workspace_repository, member_repository, audit_log_repository)


def get_project_service(
    project_repository: ProjectRepository = Depends(get_project_repository),
    member_repository: ProjectMemberRepository = Depends(get_project_member_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> ProjectService:
    return ProjectService(project_repository, member_repository, audit_log_repository)


def get_invitation_repository(db: AsyncSession = Depends(get_db)) -> InvitationRepository:
    return InvitationRepository(db)


def get_invitation_service(
    invitation_repository: InvitationRepository = Depends(get_invitation_repository),
    member_repository: OrganizationMemberRepository = Depends(get_organization_member_repository),
    user_repository: UserRepository = Depends(get_user_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> InvitationService:
    return InvitationService(
        invitation_repository, member_repository, user_repository, audit_log_repository
    )
