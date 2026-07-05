"""Provider Adapter Pattern (docs/05-task.md Phase 15;
docs/02-architecture.md sections 82-83): every provider implements the
same interface (`generate`/`stream`/`token_count`/`health_check`/
`cost_estimate`) so `LLMGateway` and everything above it never depends on
a specific provider's SDK or wire format.

Errors are classified into a small hierarchy so `gateway.py`'s retry/
fallback logic (docs/02-architecture.md section 86 — "retry only for
transient failures, never retry invalid requests") can react correctly
without each provider reimplementing that policy: `TransientProviderError`
(timeout, 5xx, 429 — retry, then fall back), `InvalidRequestError` (400 —
the request itself is broken; retrying elsewhere won't help, fail
immediately), `ProviderAuthError` (401/403 — this provider's credentials
are bad, skip straight to the next one), `ProviderNotConfiguredError`
(no API key/unreachable — never even attempted).
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass
class LLMMessage:
    role: Role
    content: str


@dataclass
class CompletionResult:
    text: str
    input_tokens: int
    output_tokens: int
    finish_reason: str | None = None


@dataclass
class StreamChunk:
    delta_text: str
    done: bool = False
    # Only populated on the final chunk (`done=True`) — most providers only
    # report token usage once streaming completes, not per-chunk.
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProviderError(Exception):
    def __init__(self, message: str, *, provider: str):
        super().__init__(message)
        self.message = message
        self.provider = provider


class TransientProviderError(LLMProviderError):
    """Timeout, 5xx, or rate-limited (429) — worth retrying/falling back."""


class InvalidRequestError(LLMProviderError):
    """The request itself is malformed (400) — retrying anywhere won't help."""


class ProviderAuthError(LLMProviderError):
    """This provider rejected the credentials (401/403) — skip to the next."""


class ProviderNotConfiguredError(LLMProviderError):
    """No API key set / endpoint unreachable — never attempted at all."""


@dataclass
class ModelCost:
    input_cost_usd: float
    output_cost_usd: float

    @property
    def total_usd(self) -> float:
        return self.input_cost_usd + self.output_cost_usd


@dataclass
class ProviderRequestOptions:
    temperature: float = 0.7
    max_output_tokens: int | None = None
    json_mode: bool = False
    tools: list[dict] | None = None
    extra: dict = field(default_factory=dict)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> CompletionResult: ...

    @abstractmethod
    def stream(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> AsyncIterator[StreamChunk]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    def token_count(self, text: str) -> int:
        # A real, deterministic, model-agnostic estimate (not every
        # provider exposes its own tokenizer over HTTP) — reuses Phase 14's
        # tiktoken-based counter rather than a length heuristic.
        from app.core.token_budget import count_tokens

        return count_tokens(text)

    def cost_estimate(self, input_tokens: int, output_tokens: int, model: str) -> ModelCost:
        from app.core.llm.registry import get_model_spec

        spec = get_model_spec(self.name, model)
        return ModelCost(
            input_cost_usd=(input_tokens / 1_000_000) * spec.price_per_1m_input,
            output_cost_usd=(output_tokens / 1_000_000) * spec.price_per_1m_output,
        )
