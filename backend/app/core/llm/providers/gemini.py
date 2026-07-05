"""Google Gemini's `generateContent`/`streamGenerateContent` API — a third
distinct wire format: no OpenAI-style `role: "system"`/`"assistant"`
(Gemini uses `"model"` for the assistant turn and a separate
`systemInstruction` field), and streaming is plain SSE of full response
objects (`alt=sse`), not delta-only chunks."""

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

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _split_system(messages: list[LLMMessage]) -> tuple[str | None, list[LLMMessage]]:
    system_parts = [m.content for m in messages if m.role == "system"]
    rest = [m for m in messages if m.role != "system"]
    return ("\n\n".join(system_parts) or None, rest)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str | None):
        self.api_key = api_key

    def _require_key(self) -> str:
        if not self.api_key:
            raise ProviderNotConfiguredError(
                "gemini API key is not configured.", provider=self.name
            )
        return self.api_key

    def _body(
        self, messages: list[LLMMessage], options: ProviderRequestOptions
    ) -> dict:
        system, rest = _split_system(messages)
        generation_config: dict = {"temperature": options.temperature}
        if options.max_output_tokens is not None:
            generation_config["maxOutputTokens"] = options.max_output_tokens
        if options.json_mode:
            generation_config["responseMimeType"] = "application/json"
        body: dict = {
            "contents": [
                {
                    "role": "model" if m.role == "assistant" else "user",
                    "parts": [{"text": m.content}],
                }
                for m in rest
            ],
            "generationConfig": generation_config,
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return body

    async def generate(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> CompletionResult:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{_BASE_URL}/models/{model}:generateContent",
                    params={"key": self._require_key()},
                    json=self._body(messages, options),
                )
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc
        raise_for_provider_status(response, provider=self.name)
        data = response.json()
        candidate = data["candidates"][0]
        text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
        usage = data.get("usageMetadata", {})
        return CompletionResult(
            text=text,
            input_tokens=usage.get("promptTokenCount", 0),
            output_tokens=usage.get("candidatesTokenCount", 0),
            finish_reason=candidate.get("finishReason"),
        )

    async def stream(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> AsyncIterator[StreamChunk]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{_BASE_URL}/models/{model}:streamGenerateContent",
                    params={"key": self._require_key(), "alt": "sse"},
                    json=self._body(messages, options),
                ) as response:
                    raise_for_provider_status(response, provider=self.name)
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        chunk = json.loads(line[len("data: ") :])
                        candidate = chunk["candidates"][0]
                        text = "".join(
                            part.get("text", "") for part in candidate["content"]["parts"]
                        )
                        usage = chunk.get("usageMetadata")
                        if candidate.get("finishReason"):
                            yield StreamChunk(
                                delta_text=text,
                                done=True,
                                input_tokens=usage.get("promptTokenCount") if usage else None,
                                output_tokens=usage.get("candidatesTokenCount") if usage else None,
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
                response = await client.get(
                    f"{_BASE_URL}/models", params={"key": self.api_key}
                )
            return response.status_code < 400
        except httpx.HTTPError:
            return False
