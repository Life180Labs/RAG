import uuid

from sqlalchemy import select

from app.models.vector_index import IndexVersion, VectorIndex
from app.repositories.base import BaseRepository


class VectorIndexRepository(BaseRepository[VectorIndex]):
    model = VectorIndex

    async def list_by_embedding_version(self, embedding_version_id: uuid.UUID) -> list[VectorIndex]:
        result = await self.session.execute(
            select(VectorIndex)
            .where(VectorIndex.embedding_version_id == embedding_version_id)
            .order_by(VectorIndex.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_embedding_version_and_provider(
        self, embedding_version_id: uuid.UUID, provider: str
    ) -> VectorIndex | None:
        result = await self.session.execute(
            select(VectorIndex).where(
                VectorIndex.embedding_version_id == embedding_version_id,
                VectorIndex.provider == provider,
            )
        )
        return result.scalar_one_or_none()


class IndexVersionRepository(BaseRepository[IndexVersion]):
    model = IndexVersion

    async def list_by_vector_index(self, vector_index_id: uuid.UUID) -> list[IndexVersion]:
        result = await self.session.execute(
            select(IndexVersion)
            .where(IndexVersion.vector_index_id == vector_index_id)
            .order_by(IndexVersion.version.desc())
        )
        return list(result.scalars().all())
