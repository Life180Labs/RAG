import uuid

from sqlalchemy import select

from app.models.provider_credential import ProviderCredential
from app.repositories.base import BaseRepository


class ProviderCredentialRepository(BaseRepository[ProviderCredential]):
    model = ProviderCredential

    async def get_by_org_and_provider(
        self, organization_id: uuid.UUID, provider: str
    ) -> ProviderCredential | None:
        result = await self.session.execute(
            select(ProviderCredential).where(
                ProviderCredential.organization_id == organization_id,
                ProviderCredential.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_organization(self, organization_id: uuid.UUID) -> list[ProviderCredential]:
        result = await self.session.execute(
            select(ProviderCredential)
            .where(ProviderCredential.organization_id == organization_id)
            .order_by(ProviderCredential.provider)
        )
        return list(result.scalars().all())
