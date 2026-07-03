import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.membership import ResourceStatus
from app.schemas.validators import validate_name, validate_slug


class WorkspaceCreate(BaseModel):
    name: str
    slug: str

    _validate_name = field_validator("name")(validate_name)
    _validate_slug = field_validator("slug")(validate_slug)


class WorkspaceUpdate(BaseModel):
    name: str

    _validate_name = field_validator("name")(validate_name)


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    status: ResourceStatus
    created_at: datetime
    updated_at: datetime
