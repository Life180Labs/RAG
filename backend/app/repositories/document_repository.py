import uuid

from sqlalchemy import select

from app.models.document import Document, DocumentVersion, UploadSession
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def get_active_by_id(self, id_: uuid.UUID) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.id == id_, Document.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_including_deleted(self, id_: uuid.UUID) -> Document | None:
        result = await self.session.execute(select(Document).where(Document.id == id_))
        return result.scalar_one_or_none()

    async def get_by_hash_in_repository(
        self, repository_id: uuid.UUID, sha256_hash: str
    ) -> Document | None:
        result = await self.session.execute(
            select(Document).where(
                Document.repository_id == repository_id,
                Document.sha256_hash == sha256_hash,
                Document.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_repository(
        self, repository_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Document]:
        result = await self.session.execute(
            select(Document)
            .where(Document.repository_id == repository_id, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class DocumentVersionRepository(BaseRepository[DocumentVersion]):
    model = DocumentVersion

    async def list_by_document(self, document_id: uuid.UUID) -> list[DocumentVersion]:
        result = await self.session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
        )
        return list(result.scalars().all())


class UploadSessionRepository(BaseRepository[UploadSession]):
    model = UploadSession
