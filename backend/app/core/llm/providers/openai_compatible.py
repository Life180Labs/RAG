"""Shared implementation for the three providers that speak the exact
same `/chat/completions` wire format (docs/05-task.md Phase 15): OpenAI
itself, Groq, and OpenRouter. Duplicating this per-provider would just be
three copies of identical request/response handling differing only in
base URL, auth header, and provider name — the same reasoning that keeps
`worker/common/embedding_providers` from having a separate class per
`fastembed`-backed local model.
"""

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


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, *, name: str, base_url: str, api_key: str | None):
        self.name = name
        self.base_url = base_url
        self.api_key = api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise ProviderNotConfiguredError(
                f"{self.name} API key is not configured.", provider=self.name
            )
        return self.api_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._require_key()}"}

    def _body(
        self,
        messages: list[LLMMessage],
        model: str,
        options: ProviderRequestOptions,
        *,
        stream: bool,
    ) -> dict:
        body = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": options.temperature,
            "stream": stream,
        }
        if options.max_output_tokens is not None:
            body["max_tokens"] = options.max_output_tokens
        if options.json_mode:
            body["response_format"] = {"type": "json_object"}
        if options.tools:
            body["tools"] = options.tools
        return body

    async def generate(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> CompletionResult:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._body(messages, model, options, stream=False),
                )
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc
        raise_for_provider_status(response, provider=self.name)
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return CompletionResult(
            text=choice["message"]["content"] or "",
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason"),
        )

    async def stream(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> AsyncIterator[StreamChunk]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._body(messages, model, options, stream=True),
                ) as response:
                    raise_for_provider_status(response, provider=self.name)
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[len("data: ") :]
                        if payload == "[DONE]":
                            yield StreamChunk(delta_text="", done=True)
                            return
                        chunk = json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        text = delta.get("content") or ""
                        usage = chunk.get("usage")
                        if usage:
                            yield StreamChunk(
                                delta_text=text,
                                done=False,
                                input_tokens=usage.get("prompt_tokens"),
                                output_tokens=usage.get("completion_tokens"),
                            )
                        elif text:
                            yield StreamChunk(delta_text=text)
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models", headers=self._headers())
            return response.status_code < 400
        except httpx.HTTPError:
            return False
