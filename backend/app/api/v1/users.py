import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, field_validator

from app.api.deps import get_current_user, get_user_service
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.user import UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Full name must not be empty.")
        return stripped


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.get("/me", response_model=SuccessResponse[UserRead])
async def get_me(
    request: Request, current_user: User = Depends(get_current_user)
) -> SuccessResponse[UserRead]:
    return SuccessResponse(
        data=UserRead.model_validate(current_user), request_id=_request_id(request)
    )


@router.patch("/me", response_model=SuccessResponse[UserRead])
async def update_me(
    payload: UpdateProfileRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> SuccessResponse[UserRead]:
    updated_user = await user_service.update_profile(current_user.id, full_name=payload.full_name)
    return SuccessResponse(
        data=UserRead.model_validate(updated_user), request_id=_request_id(request)
    )
