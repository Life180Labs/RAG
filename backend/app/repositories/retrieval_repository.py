import uuid

from sqlalchemy import select

from app.models.chunk import Chunk
from app.models.retrieval import Retrieval, RetrievalResult
from app.repositories.base import BaseRepository


class RetrievalRepository(BaseRepository[Retrieval]):
    model = Retrieval

    async def list_by_vector_index(
        self, vector_index_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Retrieval]:
        result = await self.session.execute(
            select(Retrieval)
            .where(Retrieval.vector_index_id == vector_index_id)
            .order_by(Retrieval.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class RetrievalResultRepository(BaseRepository[RetrievalResult]):
    model = RetrievalResult

    async def list_with_chunks(
        self, retrieval_id: uuid.UUID
    ) -> list[tuple[RetrievalResult, Chunk]]:
        result = await self.session.execute(
            select(RetrievalResult, Chunk)
            .join(Chunk, Chunk.id == RetrievalResult.chunk_id)
            .where(RetrievalResult.retrieval_id == retrieval_id)
            .order_by(RetrievalResult.rank)
        )
        return list(result.all())
