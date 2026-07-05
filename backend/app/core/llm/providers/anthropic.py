"""Anthropic Messages API — a real, distinct wire format from the OpenAI
family: the system prompt is a top-level field, not a `role: "system"`
message, and streaming is named SSE events (`content_block_delta`, etc.)
rather than one uniform `data: {...}` shape.

`ProviderRequestOptions.json_mode` is a documented no-op here — unlike
OpenAI/Groq/OpenRouter's `response_format` or Gemini/Ollama's
`responseMimeType`/`format`, Anthropic has no equivalent strict-JSON
request flag; structured output there requires tool-use or prefill
tricks this provider doesn't implement, so a caller relying on JSON mode
should route to a provider that actually enforces it rather than assume
Anthropic silently does the same thing."""

import json
from collections.abc import AsyncIterator

import httpx

from app.core.llm.base import (
    CompletionResult,
    LLMMessage,
    LLMProvider,
    ProviderNotConfiguredError,
    ProviderRequestOptions,
    StreamChunk,
)
from app.core.llm.providers._http import raise_for_provider_status, wrap_transport_error

_API_VERSION = "2023-06-01"
_BASE_URL = "https://api.anthropic.com/v1"
_DEFAULT_MAX_TOKENS = 4096


def _split_system(messages: list[LLMMessage]) -> tuple[str | None, list[LLMMessage]]:
    system_parts = [m.content for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]
    return ("\n\n".join(system_parts) or None, rest)


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise ProviderNotConfiguredError(
                "anthropic API key is not configured.", provider=self.name
            )
        return self.api_key

    def _headers(self) -> dict:
        return {
            "x-api-key": self._require_key(),
            "anthropic-version": _API_VERSION,
        }

    def _body(
        self,
        messages: list[LLMMessage],
        model: str,
        options: ProviderRequestOptions,
        *,
        stream: bool,
    ) -> dict:
        system, rest = _split_system(messages)
        body = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in rest],
            "max_tokens": options.max_output_tokens or _DEFAULT_MAX_TOKENS,
            "temperature": options.temperature,
            "stream": stream,
        }
        if system:
            body["system"] = system
        if options.tools:
            body["tools"] = options.tools
        return body

    async def generate(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> CompletionResult:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{_BASE_URL}/messages",
                    headers=self._headers(),
                    json=self._body(messages, model, options, stream=False),
                )
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc
        raise_for_provider_status(response, provider=self.name)
        data = response.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {})
        return CompletionResult(
            text=text,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            finish_reason=data.get("stop_reason"),
        )

    async def stream(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> AsyncIterator[StreamChunk]:
        input_tokens = None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{_BASE_URL}/messages",
                    headers=self._headers(),
                    json=self._body(messages, model, options, stream=True),
                ) as response:
                    raise_for_provider_status(response, provider=self.name)
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        event = json.loads(line[len("data: ") :])
                        event_type = event.get("type")
                        if event_type == "message_start":
                            input_tokens = event["message"]["usage"].get("input_tokens")
                        elif event_type == "content_block_delta":
                            text = event["delta"].get("text", "")
                            if text:
                                yield StreamChunk(delta_text=text)
                        elif event_type == "message_delta":
                            output_tokens = event.get("usage", {}).get("output_tokens")
                            yield StreamChunk(
                                delta_text="",
                                done=True,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                            )
                            return
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{_BASE_URL}/messages",
                    headers=self._headers(),
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                )
            return response.status_code < 500
        except httpx.HTTPError:
            return False
