import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.llm_request import LLMRequestStatus


class ModelSpecRead(BaseModel):
    provider: str
    model: str
    context_window: int
    price_per_1m_input: float
    price_per_1m_output: float
    supports_streaming: bool
    supports_json_mode: bool
    supports_vision: bool
    supports_function_calling: bool
    supports_reasoning: bool
    is_fast: bool
    is_reasoning: bool


class ProviderHealth(BaseModel):
    provider: str
    configured: bool
    healthy: bool


class LLMRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prompt_id: uuid.UUID
    provider: str
    model: str
    routing_hint: str | None
    input_text: str
    output_text: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float | None
    latency_ms: int | None
    stream: bool
    json_mode: bool
    attempted_providers: list[dict] | None
    status: LLMRequestStatus
    status_message: str | None
    created_at: datetime
    updated_at: datetime


class CreateCompletionRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    routing_hint: str | None = None
    json_mode: bool = False

    @model_validator(mode="after")
    def _provider_and_model_together(self) -> "CreateCompletionRequest":
        if bool(self.provider) != bool(self.model):
            raise ValueError(
                "provider and model must be given together, or both omitted to use "
                "routing_hint (or the default model) instead."
            )
        return self
