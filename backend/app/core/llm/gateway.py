"""LLM Gateway (docs/05-task.md Phase 15; docs/02-architecture.md
sections 82, 86): the single entry point everything else in the backend
calls through — `Prompt -> Gateway -> Provider Adapter -> Model ->
Response` — so business logic never imports a specific provider module.

Retry & Fallback policy (section 86, "retry only for transient failures,
never retry invalid requests"):

- `InvalidRequestError` — the request itself is malformed for that
  provider's wire format (almost certainly a bug in how we built it, not
  a transient condition another provider would happily accept) — raised
  immediately, no retry, no fallback to a different provider either.
- `ProviderAuthError` / `ProviderNotConfiguredError` — this provider's
  credentials are bad or absent; retrying the same provider can't help,
  but a *different* provider's credentials might be fine — skip straight
  to the next provider in the fallback chain, no retry.
- `TransientProviderError` (timeout, 5xx, 429) — retried on the same
  provider up to `MAX_ATTEMPTS_PER_PROVIDER` times with exponential
  backoff before falling back to the next provider.

`DEFAULT_FALLBACK_ORDER` is this codebase's adaptation of
docs/02-architecture.md section 86's example order (`OpenAI -> Azure
OpenAI -> Anthropic -> OpenRouter -> Groq`) to the six providers
docs/05-task.md Phase 15 actually lists (no Azure OpenAI deliverable this
phase) — cloud providers first, `ollama` last since it's only ever the
right choice when nothing else is configured or reachable (the
`"offline"` routing hint routes to it directly instead of waiting for
every cloud provider to fail first).
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.core.llm.base import (
    CompletionResult,
    InvalidRequestError,
    LLMMessage,
    ProviderAuthError,
    ProviderNotConfiguredError,
    ProviderRequestOptions,
    StreamChunk,
    TransientProviderError,
)
from app.core.llm.factory import get_provider
from app.core.llm.registry import DEFAULT_MODEL_BY_PROVIDER
from app.core.llm.router import RoutingHint, select_model

DEFAULT_FALLBACK_ORDER = ["openai", "anthropic", "groq", "openrouter", "gemini", "ollama"]
MAX_ATTEMPTS_PER_PROVIDER = 2
RETRY_BACKOFF_SECONDS = 0.5


@dataclass
class AttemptRecord:
    provider: str
    model: str
    error: str | None = None


class AllProvidersFailedError(Exception):
    def __init__(self, attempts: list[AttemptRecord]):
        self.attempts = attempts
        tried = ", ".join(f"{a.provider}:{a.error}" for a in attempts)
        super().__init__(f"Every provider in the fallback chain failed — {tried}")


def _build_fallback_order(initial_provider: str) -> list[str]:
    rest = [p for p in DEFAULT_FALLBACK_ORDER if p != initial_provider]
    return [initial_provider, *rest]


def _model_for_provider(provider_name: str, initial_provider: str, initial_model: str) -> str:
    if provider_name == initial_provider:
        return initial_model
    return DEFAULT_MODEL_BY_PROVIDER[provider_name]


class LLMGateway:
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        routing_hint: RoutingHint | None = None,
        provider: str | None = None,
        model: str | None = None,
        options: ProviderRequestOptions | None = None,
    ) -> tuple[CompletionResult, str, str, list[AttemptRecord]]:
        options = options or ProviderRequestOptions()
        spec = select_model(
            routing_hint=routing_hint, explicit_provider=provider, explicit_model=model
        )
        attempts: list[AttemptRecord] = []

        for provider_name in _build_fallback_order(spec.provider):
            model_name = _model_for_provider(provider_name, spec.provider, spec.model)
            llm_provider = get_provider(provider_name)

            for attempt_index in range(MAX_ATTEMPTS_PER_PROVIDER):
                try:
                    result = await llm_provider.generate(messages, model_name, options)
                    attempts.append(AttemptRecord(provider_name, model_name))
                    return result, provider_name, model_name, attempts
                except InvalidRequestError as exc:
                    attempts.append(AttemptRecord(provider_name, model_name, exc.message))
                    raise
                except (ProviderNotConfiguredError, ProviderAuthError) as exc:
                    attempts.append(AttemptRecord(provider_name, model_name, exc.message))
                    break
                except TransientProviderError as exc:
                    if attempt_index < MAX_ATTEMPTS_PER_PROVIDER - 1:
                        await asyncio.sleep(RETRY_BACKOFF_SECONDS * (2**attempt_index))
                        continue
                    attempts.append(AttemptRecord(provider_name, model_name, exc.message))
                    break

        raise AllProvidersFailedError(attempts)

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        routing_hint: RoutingHint | None = None,
        provider: str | None = None,
        model: str | None = None,
        options: ProviderRequestOptions | None = None,
    ) -> AsyncIterator[tuple[StreamChunk, str, str, list[AttemptRecord]]]:
        """Yields `(chunk, provider_used, model_used, attempts)`. Fallback
        only happens before the first content chunk is yielded — once the
        caller has already seen partial output, silently restarting on a
        different provider would just confuse whoever's watching the
        stream, so a mid-stream failure propagates as-is instead."""
        options = options or ProviderRequestOptions()
        spec = select_model(
            routing_hint=routing_hint, explicit_provider=provider, explicit_model=model
        )
        attempts: list[AttemptRecord] = []
        any_yielded = False

        for provider_name in _build_fallback_order(spec.provider):
            model_name = _model_for_provider(provider_name, spec.provider, spec.model)
            llm_provider = get_provider(provider_name)

            for attempt_index in range(MAX_ATTEMPTS_PER_PROVIDER):
                try:
                    async for chunk in llm_provider.stream(messages, model_name, options):
                        any_yielded = any_yielded or bool(chunk.delta_text)
                        yield chunk, provider_name, model_name, attempts
                    attempts.append(AttemptRecord(provider_name, model_name))
                    return
                except InvalidRequestError as exc:
                    attempts.append(AttemptRecord(provider_name, model_name, exc.message))
                    raise
                except (ProviderNotConfiguredError, ProviderAuthError) as exc:
                    attempts.append(AttemptRecord(provider_name, model_name, exc.message))
                    if any_yielded:
                        raise
                    break
                except TransientProviderError as exc:
                    if any_yielded:
                        raise
                    if attempt_index < MAX_ATTEMPTS_PER_PROVIDER - 1:
                        await asyncio.sleep(RETRY_BACKOFF_SECONDS * (2**attempt_index))
                        continue
                    attempts.append(AttemptRecord(provider_name, model_name, exc.message))
                    break

        raise AllProvidersFailedError(attempts)
