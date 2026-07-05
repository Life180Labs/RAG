"""Unit tests for query condensation/summarization fallback behavior —
no network, no database (a stub gateway stands in for LLMGateway)."""

import pytest

from app.core.conversation.condensation import condense_query
from app.core.conversation.summarization import summarize_messages
from app.core.llm.base import CompletionResult


class _StubGateway:
    def __init__(self, *, result=None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.calls = 0

    async def generate(self, messages, **kwargs):
        self.calls += 1
        if self._error:
            raise self._error
        return self._result, "stub", "stub-model", []


@pytest.mark.asyncio
async def test_condense_query_returns_raw_query_when_no_history():
    gateway = _StubGateway()
    result = await condense_query(gateway, "", "What about contractors?")
    assert result == "What about contractors?"
    assert gateway.calls == 0


@pytest.mark.asyncio
async def test_condense_query_returns_llm_result_when_history_present():
    gateway = _StubGateway(
        result=CompletionResult(
            text="What is the annual leave policy for contractors?",
            input_tokens=10,
            output_tokens=8,
        )
    )
    result = await condense_query(
        gateway,
        "User: What is the annual leave policy?\nAssistant: 20 days a year.",
        "What about contractors?",
    )
    assert result == "What is the annual leave policy for contractors?"
    assert gateway.calls == 1


@pytest.mark.asyncio
async def test_condense_query_falls_back_to_raw_query_on_gateway_failure():
    gateway = _StubGateway(error=RuntimeError("all providers failed"))
    result = await condense_query(gateway, "some history", "What about contractors?")
    assert result == "What about contractors?"


@pytest.mark.asyncio
async def test_condense_query_falls_back_when_llm_returns_empty_text():
    gateway = _StubGateway(result=CompletionResult(text="   ", input_tokens=1, output_tokens=0))
    result = await condense_query(gateway, "history", "raw query")
    assert result == "raw query"


@pytest.mark.asyncio
async def test_summarize_messages_returns_llm_result():
    gateway = _StubGateway(
        result=CompletionResult(text="A concise summary.", input_tokens=50, output_tokens=10)
    )
    result = await summarize_messages(gateway, "User: hi\nAssistant: hello")
    assert result == "A concise summary."


@pytest.mark.asyncio
async def test_summarize_messages_propagates_gateway_failure():
    gateway = _StubGateway(error=RuntimeError("all providers failed"))
    with pytest.raises(RuntimeError):
        await summarize_messages(gateway, "some transcript")
