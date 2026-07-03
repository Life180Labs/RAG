"""RBAC dependency + DI wiring for document routes.

Documents are scoped by `repository_id` at creation but addressed by
their own `document_id` afterward, so they need their own tenant-isolation
dependency rather than reusing `require_repository_role` directly (which
expects a `repository_id` path parameter) — this one loads the document
first, then checks membership on *its* repository.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository, get_current_user
from app.api.tenancy_deps import get_repository_member_repository, get_repository_repository
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.storage_adapter import StorageAdapter, get_storage_adapter
from app.db.session import get_db
from app.models.document import Document
from app.models.membership import MemberRole, role_meets_minimum
from app.models.repository import RepositoryMember
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import (
    DocumentRepository,
    DocumentVersionRepository,
    UploadSessionRepository,
)
from app.repositories.membership_repository import RepositoryMemberRepository
from app.repositories.repository_repository import RepositoryRepository
from app.services.document_service import DocumentService


def get_document_repository(db: AsyncSession = Depends(get_db)) -> DocumentRepository:
    return DocumentRepository(db)


def get_document_version_repository(
    db: AsyncSession = Depends(get_db),
) -> DocumentVersionRepository:
    return DocumentVersionRepository(db)


def get_upload_session_repository(db: AsyncSession = Depends(get_db)) -> UploadSessionRepository:
    return UploadSessionRepository(db)


def get_document_service(
    document_repository: DocumentRepository = Depends(get_document_repository),
    version_repository: DocumentVersionRepository = Depends(get_document_version_repository),
    upload_session_repository: UploadSessionRepository = Depends(get_upload_session_repository),
    repository_repository: RepositoryRepository = Depends(get_repository_repository),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
    storage_adapter: StorageAdapter = Depends(get_storage_adapter),
) -> DocumentService:
    return DocumentService(
        document_repository,
        version_repository,
        upload_session_repository,
        repository_repository,
        audit_log_repository,
        storage_adapter,
    )


@dataclass
class DocumentAccess:
    document: Document
    membership: RepositoryMember


def require_document_role(minimum: MemberRole, *, include_deleted: bool = False):
    """`Depends(require_document_role(MemberRole.ADMIN))` on a route with a
    `document_id` path parameter. Pass `include_deleted=True` for routes
    (like restore) that must operate on a soft-deleted document."""

    async def _dependency(
        document_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        document_repo: DocumentRepository = Depends(get_document_repository),
        member_repo: RepositoryMemberRepository = Depends(get_repository_member_repository),
    ) -> DocumentAccess:
        document = (
            await document_repo.get_including_deleted(document_id)
            if include_deleted
            else await document_repo.get_active_by_id(document_id)
        )
        if document is None:
            raise NotFoundError("Document not found.", code="DOCUMENT_NOT_FOUND")

        membership = await member_repo.get_membership(document.repository_id, current_user.id)
        if membership is None:
            raise ForbiddenError(
                "You are not a member of this document's repository.", code="NOT_A_MEMBER"
            )
        if not role_meets_minimum(membership.role, minimum):
            raise ForbiddenError("Insufficient role for this action.", code="FORBIDDEN")

        return DocumentAccess(document=document, membership=membership)

    return _dependency
