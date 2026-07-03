import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.membership import InvitationStatus, MemberRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: MemberRole


class InvitationAccept(BaseModel):
    token: str


class InvitationReject(BaseModel):
    token: str


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    role: MemberRole
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
