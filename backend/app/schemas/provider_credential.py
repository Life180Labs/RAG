import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.provider_credential import ALLOWED_PROVIDERS


class ProviderCredentialCreate(BaseModel):
    provider: str
    api_key: str

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in ALLOWED_PROVIDERS:
            raise ValueError(
                f"'{value}' is not a configurable provider. Allowed: "
                f"{', '.join(sorted(ALLOWED_PROVIDERS))}."
            )
        return normalized

    @field_validator("api_key")
    @classmethod
    def _validate_api_key(cls, value: str) -> str:
        if len(value.strip()) < 8:
            raise ValueError("api_key looks too short to be a real credential.")
        return value


class ProviderCredentialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    provider: str
    last_four: str
    created_at: datetime
    updated_at: datetime
