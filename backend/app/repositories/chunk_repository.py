import uuid

from sqlalchemy import func, select

from app.models.chunk import Chunk, DocumentChunkSet
from app.repositories.base import BaseRepository


class ChunkSetRepository(BaseRepository[DocumentChunkSet]):
    model = DocumentChunkSet

    async def list_by_document(self, document_id: uuid.UUID) -> list[DocumentChunkSet]:
        result = await self.session.execute(
            select(DocumentChunkSet)
            .where(DocumentChunkSet.document_id == document_id)
            .order_by(DocumentChunkSet.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_document_and_strategy(
        self, document_id: uuid.UUID, strategy: str
    ) -> DocumentChunkSet | None:
        result = await self.session.execute(
            select(DocumentChunkSet).where(
                DocumentChunkSet.document_id == document_id,
                DocumentChunkSet.strategy == strategy,
            )
        )
        return result.scalar_one_or_none()


class ChunkRepository(BaseRepository[Chunk]):
    model = Chunk

    async def list_by_chunk_set(
        self, chunk_set_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Chunk]:
        result = await self.session.execute(
            select(Chunk)
            .where(Chunk.chunk_set_id == chunk_set_id)
            .order_by(Chunk.chunk_index)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_chunk_set(self, chunk_set_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Chunk).where(Chunk.chunk_set_id == chunk_set_id)
        )
        return result.scalar_one()
