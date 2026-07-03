"""Shared response envelopes per docs/07-master_prompt.md Response Standards."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    metadata: dict[str, Any] = {}
    request_id: str


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str
