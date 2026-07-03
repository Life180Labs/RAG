"""Repository business logic.

Creating a repository always makes the creator its OWNER, mirroring
Organization/Workspace/Project (see docs/03-database.md section 6).

"Clone/Duplicate/Export/Import" (docs/05-task.md Phase 3 Repository
Features) are intentionally not implemented here — they only make sense
once documents/embeddings exist to actually copy or move, which is a
later phase. Statistics counters exist and default to zero for the same
reason: they're incremented by the document/chunk/embedding phases.
"""

import uuid
from datetime import UTC, datetime

from app.core.exceptions import ConflictError
from app.models.audit_log import AuditLog
from app.models.membership import MemberRole, ResourceStatus
from app.models.repository import Repository, RepositoryMember
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.membership_repository import RepositoryMemberRepository
from app.repositories.repository_repository import RepositoryRepository


class RepositoryService:
    def __init__(
        self,
        repository_repository: RepositoryRepository,
        member_repository: RepositoryMemberRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.repositories = repository_repository
        self.members = member_repository
        self.audit_logs = audit_log_repository

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def create(
        self,
        *,
        project_id: uuid.UUID,
        creator_id: uuid.UUID,
        name: str,
        slug: str,
        description: str | None,
    ) -> Repository:
        existing = await self.repositories.get_by_slug_in_project(project_id, slug)
        if existing is not None:
            raise ConflictError(
                "A repository with this slug already exists in the project.", code="SLUG_TAKEN"
            )

        repository = Repository(
            project_id=project_id,
            name=name,
            slug=slug,
            description=description,
            status=ResourceStatus.ACTIVE,
            created_by=creator_id,
            updated_by=creator_id,
        )
        await self.repositories.add(repository)

        await self.members.add(
            RepositoryMember(repository_id=repository.id, user_id=creator_id, role=MemberRole.OWNER)
        )

        await self._record_audit(
            user_id=creator_id, action="repository.create", resource=str(repository.id)
        )
        return repository

    async def list_by_project(self, project_id: uuid.UUID) -> list[Repository]:
        return await self.repositories.list_by_project(project_id)

    async def search(self, project_id: uuid.UUID, query: str) -> list[Repository]:
        return await self.repositories.search_by_project(project_id, query)

    async def update(
        self,
        repository: Repository,
        *,
        name: str,
        description: str | None,
        actor_id: uuid.UUID,
    ) -> Repository:
        repository.name = name
        repository.description = description
        repository.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="repository.update", resource=str(repository.id)
        )
        return repository

    async def update_settings(
        self,
        repository: Repository,
        *,
        default_chunk_strategy: str | None,
        default_embedding_model: str | None,
        default_retriever: str | None,
        default_reranker: str | None,
        default_prompt_version: str | None,
        actor_id: uuid.UUID,
    ) -> Repository:
        repository.default_chunk_strategy = default_chunk_strategy
        repository.default_embedding_model = default_embedding_model
        repository.default_retriever = default_retriever
        repository.default_reranker = default_reranker
        repository.default_prompt_version = default_prompt_version
        repository.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="repository.update_settings", resource=str(repository.id)
        )
        return repository

    async def archive(self, repository: Repository, *, actor_id: uuid.UUID) -> Repository:
        repository.status = ResourceStatus.ARCHIVED
        repository.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="repository.archive", resource=str(repository.id)
        )
        return repository

    async def restore(self, repository: Repository, *, actor_id: uuid.UUID) -> Repository:
        repository.status = ResourceStatus.ACTIVE
        repository.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="repository.restore", resource=str(repository.id)
        )
        return repository

    async def soft_delete(self, repository: Repository, *, actor_id: uuid.UUID) -> None:
        repository.deleted_at = datetime.now(UTC)
        repository.updated_by = actor_id
        await self._record_audit(
            user_id=actor_id, action="repository.delete", resource=str(repository.id)
        )

    async def activity(self, repository_id: uuid.UUID) -> list[AuditLog]:
        return await self.audit_logs.list_for_resource(str(repository_id))
