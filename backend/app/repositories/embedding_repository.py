import uuid

from sqlalchemy import func, select

from app.models.embedding import Embedding, EmbeddingVersion
from app.repositories.base import BaseRepository


class EmbeddingVersionRepository(BaseRepository[EmbeddingVersion]):
    model = EmbeddingVersion

    async def list_by_chunk_set(self, chunk_set_id: uuid.UUID) -> list[EmbeddingVersion]:
        result = await self.session.execute(
            select(EmbeddingVersion)
            .where(EmbeddingVersion.chunk_set_id == chunk_set_id)
            .order_by(EmbeddingVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_chunk_set_and_provider(
        self, chunk_set_id: uuid.UUID, provider: str, model: str | None = None
    ) -> EmbeddingVersion | None:
        query = select(EmbeddingVersion).where(
            EmbeddingVersion.chunk_set_id == chunk_set_id,
            EmbeddingVersion.provider == provider,
        )
        if model is not None:
            query = query.where(EmbeddingVersion.model == model)
        result = await self.session.execute(query.order_by(EmbeddingVersion.created_at.desc()))
        return result.scalars().first()


class EmbeddingRepository(BaseRepository[Embedding]):
    model = Embedding

    async def list_by_version(
        self, embedding_version_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Embedding]:
        result = await self.session.execute(
            select(Embedding)
            .where(Embedding.embedding_version_id == embedding_version_id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_version(self, embedding_version_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Embedding)
            .where(Embedding.embedding_version_id == embedding_version_id)
        )
        return result.scalar_one()
