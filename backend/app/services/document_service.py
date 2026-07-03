"""Document upload/versioning business logic.

Validation (size/extension/password-protection/virus-scan-stub) happens
synchronously here, before anything is stored — the background
`finalize_upload` task's job is only to confirm the object landed in
storage, not to re-validate it (see worker/document_worker/tasks.py).

Uploading/deleting/restoring a document keeps `Repository.document_count`
and `.storage_used_bytes` in sync — this is the one statistic Phase 4
actually populates for real, since it's the phase that creates documents;
chunk/embedding/retrieval counts remain at zero until their phases exist.
"""

import io
import uuid
from datetime import UTC, datetime

from app.core.document_validation import compute_sha256, validate_upload
from app.core.exceptions import ConflictError
from app.core.storage_adapter import StorageAdapter
from app.core.task_queue import enqueue_finalize_upload
from app.models.audit_log import AuditLog
from app.models.document import (
    Document,
    DocumentStatus,
    DocumentVersion,
    UploadSession,
    UploadSessionStatus,
)
from app.models.repository import Repository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import (
    DocumentRepository,
    DocumentVersionRepository,
    UploadSessionRepository,
)
from app.repositories.repository_repository import RepositoryRepository


class DocumentService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        version_repository: DocumentVersionRepository,
        upload_session_repository: UploadSessionRepository,
        repository_repository: RepositoryRepository,
        audit_log_repository: AuditLogRepository,
        storage_adapter: StorageAdapter,
    ):
        self.documents = document_repository
        self.versions = version_repository
        self.upload_sessions = upload_session_repository
        self.repositories = repository_repository
        self.audit_logs = audit_log_repository
        self.storage = storage_adapter

    async def _record_audit(self, *, user_id: uuid.UUID, action: str, resource: str) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    def _storage_key(
        self, repository_id: uuid.UUID, document_id: uuid.UUID, version: int, filename: str
    ) -> str:
        return f"documents/{repository_id}/{document_id}/v{version}/{filename}"

    async def upload(
        self,
        *,
        repository_id: uuid.UUID,
        uploader_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> Document:
        validate_upload(filename=filename, size_bytes=len(content), content=content)
        sha256_hash = compute_sha256(content)

        existing = await self.documents.get_by_hash_in_repository(repository_id, sha256_hash)
        if existing is not None:
            raise ConflictError(
                "An identical file already exists in this repository.",
                code="DUPLICATE_DOCUMENT",
            )

        upload_session = UploadSession(
            repository_id=repository_id, user_id=uploader_id, filename=filename
        )
        await self.upload_sessions.add(upload_session)

        document_id = uuid.uuid4()
        storage_key = self._storage_key(repository_id, document_id, 1, filename)
        self.storage.upload(storage_key, io.BytesIO(content), len(content), content_type)

        now = datetime.now(UTC)
        document = Document(
            id=document_id,
            repository_id=repository_id,
            filename=filename,
            mime_type=content_type,
            size_bytes=len(content),
            sha256_hash=sha256_hash,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
            current_version=1,
            uploaded_by=uploader_id,
            created_by=uploader_id,
            updated_by=uploader_id,
        )
        await self.documents.add(document)

        await self.versions.add(
            DocumentVersion(
                document_id=document.id,
                version=1,
                filename=filename,
                mime_type=content_type,
                size_bytes=len(content),
                sha256_hash=sha256_hash,
                storage_key=storage_key,
                status=DocumentStatus.UPLOADED,
                created_at=now,
                created_by=uploader_id,
            )
        )

        upload_session.document_id = document.id
        upload_session.status = UploadSessionStatus.COMPLETED

        await self._bump_repository_stats(repository_id, document_delta=1, bytes_delta=len(content))
        await self._record_audit(
            user_id=uploader_id, action="document.upload", resource=str(document.id)
        )

        enqueue_finalize_upload(str(document.id))
        return document

    async def create_new_version(
        self,
        document: Document,
        *,
        actor_id: uuid.UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> Document:
        validate_upload(filename=filename, size_bytes=len(content), content=content)
        sha256_hash = compute_sha256(content)

        new_version_number = document.current_version + 1
        storage_key = self._storage_key(
            document.repository_id, document.id, new_version_number, filename
        )
        self.storage.upload(storage_key, io.BytesIO(content), len(content), content_type)

        now = datetime.now(UTC)
        old_size = document.size_bytes

        document.filename = filename
        document.mime_type = content_type
        document.size_bytes = len(content)
        document.sha256_hash = sha256_hash
        document.storage_key = storage_key
        document.status = DocumentStatus.UPLOADED
        document.status_message = None
        document.current_version = new_version_number
        document.updated_by = actor_id

        await self.versions.add(
            DocumentVersion(
                document_id=document.id,
                version=new_version_number,
                filename=filename,
                mime_type=content_type,
                size_bytes=len(content),
                sha256_hash=sha256_hash,
                storage_key=storage_key,
                status=DocumentStatus.UPLOADED,
                created_at=now,
                created_by=actor_id,
            )
        )

        await self._bump_repository_stats(
            document.repository_id, document_delta=0, bytes_delta=len(content) - old_size
        )
        await self._record_audit(
            user_id=actor_id, action="document.new_version", resource=str(document.id)
        )

        enqueue_finalize_upload(str(document.id))
        return document

    async def list_by_repository(self, repository_id: uuid.UUID) -> list[Document]:
        return await self.documents.list_by_repository(repository_id)

    async def list_versions(self, document_id: uuid.UUID) -> list[DocumentVersion]:
        return await self.versions.list_by_document(document_id)

    async def soft_delete(self, document: Document, *, actor_id: uuid.UUID) -> None:
        document.deleted_at = datetime.now(UTC)
        document.updated_by = actor_id
        await self._bump_repository_stats(
            document.repository_id, document_delta=-1, bytes_delta=-document.size_bytes
        )
        await self._record_audit(
            user_id=actor_id, action="document.delete", resource=str(document.id)
        )

    async def restore(self, document: Document, *, actor_id: uuid.UUID) -> Document:
        document.deleted_at = None
        document.updated_by = actor_id
        await self._bump_repository_stats(
            document.repository_id, document_delta=1, bytes_delta=document.size_bytes
        )
        await self._record_audit(
            user_id=actor_id, action="document.restore", resource=str(document.id)
        )
        return document

    def download_url(self, document: Document, expires_seconds: int = 3600) -> str | None:
        return self.storage.presigned_download_url(document.storage_key, expires_seconds)

    def download_stream(self, document: Document):
        return self.storage.open_stream(document.storage_key)

    async def _bump_repository_stats(
        self, repository_id: uuid.UUID, *, document_delta: int, bytes_delta: int
    ) -> None:
        repository: Repository | None = await self.repositories.get_active_by_id(repository_id)
        if repository is None:
            return
        repository.document_count = max(0, repository.document_count + document_delta)
        repository.storage_used_bytes = max(0, repository.storage_used_bytes + bytes_delta)
