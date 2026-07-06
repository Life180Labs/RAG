"""Unit tests for the LLM Gateway's pure logic: model registry, dynamic
routing, and retry/fallback — no network, no database."""

import pytest

from app.core.llm.base import (
    CompletionResult,
    InvalidRequestError,
    LLMMessage,
    ProviderAuthError,
    ProviderNotConfiguredError,
    StreamChunk,
    TransientProviderError,
)
from app.core.llm.factory import PROVIDER_NAMES, get_provider
from app.core.llm.gateway import AllProvidersFailedError, LLMGateway
from app.core.llm.registry import get_model_spec, list_models
from app.core.llm.router import NoMatchingModelError, select_model


def test_list_models_covers_all_six_providers():
    providers = {m.provider for m in list_models()}
    assert providers == set(PROVIDER_NAMES)


def test_select_model_explicit_returns_registered_spec():
    spec = select_model(explicit_provider="anthropic", explicit_model="claude-3-5-sonnet-20241022")
    assert spec.provider == "anthropic"


def test_select_model_explicit_unregistered_raises():
    with pytest.raises(NoMatchingModelError):
        select_model(explicit_provider="openai", explicit_model="not-a-real-model")


def test_select_model_fast_hint_returns_fast_model():
    spec = select_model(routing_hint="fast")
    assert spec.is_fast


def test_select_model_reasoning_hint_returns_reasoning_model():
    spec = select_model(routing_hint="reasoning")
    assert spec.is_reasoning


def test_select_model_large_context_returns_largest_window():
    spec = select_model(routing_hint="large_context")
    assert spec.context_window == max(m.context_window for m in list_models())


def test_select_model_low_budget_returns_cheapest():
    spec = select_model(routing_hint="low_budget")
    cheapest = min(list_models(), key=lambda m: m.price_per_1m_input + m.price_per_1m_output)
    assert spec.provider == cheapest.provider and spec.model == cheapest.model


def test_select_model_offline_returns_ollama():
    spec = select_model(routing_hint="offline")
    assert spec.provider == "ollama"


def test_select_model_default_when_no_hint():
    spec = select_model()
    assert spec.provider == "openai"


def test_factory_dispatches_all_six_providers():
    for name in PROVIDER_NAMES:
        provider = get_provider(name)
        assert provider.name == name


def test_factory_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_provider("not-a-provider")


def test_cost_estimate_uses_registry_pricing():
    provider = get_provider("openai")
    spec = get_model_spec("openai", "gpt-4o-mini")
    cost = provider.cost_estimate(1_000_000, 1_000_000, "gpt-4o-mini")
    assert cost.input_cost_usd == pytest.approx(spec.price_per_1m_input)
    assert cost.output_cost_usd == pytest.approx(spec.price_per_1m_output)


class _StubProvider:
    """A fake provider whose `generate`/`stream` raise a scripted sequence
    of outcomes, so gateway retry/fallback logic can be tested without
    any real network calls."""

    def __init__(self, name: str, outcomes: list):
        self.name = name
        self._outcomes = list(outcomes)
        self.calls = 0

    async def generate(self, messages, model, options):
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def stream(self, messages, model, options):
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        for chunk in outcome:
            yield chunk


@pytest.fixture
def gateway():
    return LLMGateway()


@pytest.mark.asyncio
async def test_gateway_generate_succeeds_on_first_provider(gateway, monkeypatch):
    result_obj = CompletionResult(text="hi", input_tokens=1, output_tokens=1)
    stub = _StubProvider("openai", [result_obj])
    monkeypatch.setattr(
        "app.core.llm.gateway.get_provider", lambda name, api_key_override=None: stub
    )

    result, provider_used, model_used, attempts = await gateway.generate(
        [LLMMessage(role="user", content="hi")], provider="openai", model="gpt-4o-mini"
    )
    assert result is result_obj
    assert provider_used == "openai"
    assert len(attempts) == 1
    assert attempts[0].error is None


@pytest.mark.asyncio
async def test_gateway_retries_transient_error_then_succeeds(gateway, monkeypatch):
    result_obj = CompletionResult(text="hi", input_tokens=1, output_tokens=1)
    stub = _StubProvider(
        "openai", [TransientProviderError("timeout", provider="openai"), result_obj]
    )
    monkeypatch.setattr(
        "app.core.llm.gateway.get_provider", lambda name, api_key_override=None: stub
    )
    monkeypatch.setattr("app.core.llm.gateway.RETRY_BACKOFF_SECONDS", 0.0)

    result, provider_used, _, attempts = await gateway.generate(
        [LLMMessage(role="user", content="hi")], provider="openai", model="gpt-4o-mini"
    )
    assert result is result_obj
    assert stub.calls == 2
    assert len(attempts) == 1  # only the final successful attempt is recorded


@pytest.mark.asyncio
async def test_gateway_invalid_request_raises_immediately_no_fallback(gateway, monkeypatch):
    stubs: dict[str, _StubProvider] = {}

    def _get(name, api_key_override=None):
        stubs.setdefault(name, _StubProvider(name, [InvalidRequestError("bad", provider=name)]))
        return stubs[name]

    monkeypatch.setattr("app.core.llm.gateway.get_provider", _get)

    with pytest.raises(InvalidRequestError):
        await gateway.generate(
            [LLMMessage(role="user", content="hi")], provider="openai", model="gpt-4o-mini"
        )
    # No fallback attempted — only the first (openai) provider was ever called.
    assert list(stubs.keys()) == ["openai"]


@pytest.mark.asyncio
async def test_gateway_not_configured_skips_to_next_provider(gateway, monkeypatch):
    result_obj = CompletionResult(text="hi", input_tokens=1, output_tokens=1)
    stubs = {
        "openai": _StubProvider(
            "openai", [ProviderNotConfiguredError("no key", provider="openai")]
        ),
        "anthropic": _StubProvider("anthropic", [result_obj]),
    }
    monkeypatch.setattr(
        "app.core.llm.gateway.get_provider", lambda name, api_key_override=None: stubs[name]
    )
    monkeypatch.setattr(
        "app.core.llm.gateway.DEFAULT_FALLBACK_ORDER", ["openai", "anthropic"]
    )

    result, provider_used, _, attempts = await gateway.generate(
        [LLMMessage(role="user", content="hi")], provider="openai", model="gpt-4o-mini"
    )
    assert provider_used == "anthropic"
    assert result is result_obj
    assert [a.provider for a in attempts] == ["openai", "anthropic"]
    assert attempts[0].error is not None
    assert attempts[1].error is None
    # No retry on the not-configured provider — called exactly once.
    assert stubs["openai"].calls == 1


@pytest.mark.asyncio
async def test_gateway_all_providers_failed_records_every_attempt(gateway, monkeypatch):
    stubs = {
        name: _StubProvider(name, [ProviderAuthError("bad creds", provider=name)])
        for name in ["openai", "anthropic"]
    }
    monkeypatch.setattr(
        "app.core.llm.gateway.get_provider", lambda name, api_key_override=None: stubs[name]
    )
    monkeypatch.setattr(
        "app.core.llm.gateway.DEFAULT_FALLBACK_ORDER", ["openai", "anthropic"]
    )

    with pytest.raises(AllProvidersFailedError) as exc_info:
        await gateway.generate(
            [LLMMessage(role="user", content="hi")], provider="openai", model="gpt-4o-mini"
        )
    assert len(exc_info.value.attempts) == 2


@pytest.mark.asyncio
async def test_gateway_stream_yields_chunks_and_stops_fallback_after_first_chunk(
    gateway, monkeypatch
):
    chunks = [StreamChunk(delta_text="hel"), StreamChunk(delta_text="lo", done=True)]
    stub = _StubProvider("openai", [chunks])
    monkeypatch.setattr(
        "app.core.llm.gateway.get_provider", lambda name, api_key_override=None: stub
    )

    collected = []
    async for chunk, provider_used, model_used, attempts in gateway.stream(  # noqa: B007
        [LLMMessage(role="user", content="hi")], provider="openai", model="gpt-4o-mini"
    ):
        collected.append(chunk.delta_text)
    assert "".join(collected) == "hello"
    assert provider_used == "openai"
