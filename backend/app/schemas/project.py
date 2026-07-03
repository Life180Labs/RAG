import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.membership import ResourceStatus
from app.schemas.validators import validate_name, validate_slug


class ProjectCreate(BaseModel):
    name: str
    slug: str

    _validate_name = field_validator("name")(validate_name)
    _validate_slug = field_validator("slug")(validate_slug)


class ProjectUpdate(BaseModel):
    name: str

    _validate_name = field_validator("name")(validate_name)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    status: ResourceStatus
    owner_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
