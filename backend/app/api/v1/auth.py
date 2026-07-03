"""Authentication endpoints.

Controllers only validate, call the service, and shape the response —
no business logic, no direct repository/DB access (docs/06-rule.md).
"""

import uuid

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_auth_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.middleware.rate_limit import rate_limiter
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.common import SuccessResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/register",
    response_model=SuccessResponse[UserRead],
    dependencies=[Depends(rate_limiter("register", limit=5, window_seconds=60))],
)
async def register(
    payload: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserRead]:
    user = await auth_service.register(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    return SuccessResponse(data=UserRead.model_validate(user), request_id=_request_id(request))


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    dependencies=[Depends(rate_limiter("login", limit=10, window_seconds=60))],
)
async def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[TokenResponse]:
    settings = get_settings()
    _user, access_token, refresh_token = await auth_service.authenticate(
        email=payload.email,
        password=payload.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
    return SuccessResponse(data=token_response, request_id=_request_id(request))


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh(
    payload: RefreshRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[TokenResponse]:
    settings = get_settings()
    access_token, refresh_token = await auth_service.refresh(refresh_token=payload.refresh_token)
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
    return SuccessResponse(data=token_response, request_id=_request_id(request))


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout(
    payload: LogoutRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[dict]:
    await auth_service.logout(refresh_token=payload.refresh_token)
    return SuccessResponse(data={"logged_out": True}, request_id=_request_id(request))


@router.post(
    "/forgot-password",
    response_model=SuccessResponse[dict],
    dependencies=[Depends(rate_limiter("forgot_password", limit=5, window_seconds=60))],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[dict]:
    settings = get_settings()
    reset_token = await auth_service.request_password_reset(email=payload.email)

    data: dict = {"message": "If the email exists, a reset link has been sent."}
    if settings.debug and reset_token is not None:
        # Dev/local convenience only — no email service exists yet. Never
        # exposed when DEBUG is false.
        data["reset_token"] = reset_token
    return SuccessResponse(data=data, request_id=_request_id(request))


@router.post("/reset-password", response_model=SuccessResponse[dict])
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[dict]:
    await auth_service.reset_password(
        reset_token=payload.reset_token, new_password=payload.new_password
    )
    return SuccessResponse(data={"reset": True}, request_id=_request_id(request))
