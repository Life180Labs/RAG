import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.token_budget import DEFAULT_RESPONSE_RESERVE_TOKENS
from app.models.prompt import PromptStatus

_DEFAULT_MODEL_CONTEXT_WINDOW = 8192


class PromptTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    name: str
    version: int
    system_prompt: str
    formatting_instructions: str | None
    output_schema: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreatePromptTemplateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    system_prompt: str = Field(..., min_length=1)
    formatting_instructions: str | None = None
    output_schema: dict | None = None


class PromptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    retrieval_id: uuid.UUID
    prompt_template_id: uuid.UUID | None
    model_context_window: int
    system_prompt_tokens: int
    conversation_tokens: int
    context_tokens: int
    query_tokens: int
    response_budget_tokens: int
    total_tokens: int
    rendered_system_prompt: str | None
    rendered_context: str | None
    rendered_prompt: str | None
    citations: list[dict] | None
    status: PromptStatus
    status_message: str | None
    created_at: datetime
    updated_at: datetime


class CreatePromptRequest(BaseModel):
    prompt_template_id: uuid.UUID | None = None
    system_prompt: str | None = Field(default=None, max_length=20000)
    formatting_instructions: str | None = None
    output_schema: dict | None = None
    model_context_window: int = Field(default=_DEFAULT_MODEL_CONTEXT_WINDOW, ge=256)
    response_reserve_tokens: int = Field(default=DEFAULT_RESPONSE_RESERVE_TOKENS, ge=0)
    order_by_page: bool = False

    @model_validator(mode="after")
    def _require_system_prompt_source(self) -> "CreatePromptRequest":
        if self.prompt_template_id is None and not self.system_prompt:
            raise ValueError(
                "Either prompt_template_id or system_prompt must be provided — a prompt needs "
                "a system prompt from somewhere."
            )
        return self
