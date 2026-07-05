"""Ollama's `/api/chat` — self-hosted, no API key. Streaming is
newline-delimited JSON (one full object per line), not SSE — a fourth
distinct wire format among this gateway's providers.

`ProviderNotConfiguredError` here means "unreachable", not "no key set"
(there is no key) — mirroring the same "real integration, but nothing to
talk to in this environment" gap Phase 8's self-hosted Qdrant/Chroma
providers would have if their containers weren't running, except Ollama
has no container in this repo's docker-compose stack at all (see
docs/03-database.md section 21 / docs/05-task.md Phase 15 for the
documented tradeoff and follow-up)."""

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
from app.core.llm.providers._http import wrap_transport_error


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _body(
        self,
        messages: list[LLMMessage],
        model: str,
        options: ProviderRequestOptions,
        *,
        stream: bool,
    ) -> dict:
        body: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "options": {"temperature": options.temperature},
        }
        if options.json_mode:
            body["format"] = "json"
        return body

    async def generate(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> CompletionResult:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=self._body(messages, model, options, stream=False),
                )
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ProviderNotConfiguredError(
                f"Ollama server unreachable at {self.base_url}: {exc}", provider=self.name
            ) from exc
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc
        data = response.json()
        return CompletionResult(
            text=data["message"]["content"],
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            finish_reason="stop" if data.get("done") else None,
        )

    async def stream(
        self, messages: list[LLMMessage], model: str, options: ProviderRequestOptions
    ) -> AsyncIterator[StreamChunk]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=self._body(messages, model, options, stream=True),
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        if chunk.get("done"):
                            yield StreamChunk(
                                delta_text="",
                                done=True,
                                input_tokens=chunk.get("prompt_eval_count"),
                                output_tokens=chunk.get("eval_count"),
                            )
                            return
                        text = chunk.get("message", {}).get("content", "")
                        if text:
                            yield StreamChunk(delta_text=text)
        except httpx.ConnectError as exc:
            raise ProviderNotConfiguredError(
                f"Ollama server unreachable at {self.base_url}: {exc}", provider=self.name
            ) from exc
        except httpx.HTTPError as exc:
            raise wrap_transport_error(exc, provider=self.name) from exc

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code < 400
        except httpx.HTTPError:
            return False
