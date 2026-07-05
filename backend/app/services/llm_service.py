"""LLM Gateway service (docs/05-task.md Phase 15).

Every completion is generated from an already-built, already-grounded
`Prompt` (Phase 14) — `create_completion` reuses `PromptService.get`
(which already validates the document/vector-index/retrieval/prompt
ownership chain) rather than re-implementing that check, then hands
`prompt.rendered_prompt` to `LLMGateway`. A completion is always
persisted, whether it succeeds or every provider in the fallback chain
fails — `AllProvidersFailedError`/`InvalidRequestError` are caught here
and turned into a `status="failed"` row with `attempted_providers`
filled in, rather than a bare 500, so a failed generation is just as
inspectable as a successful one (mirrors `PromptService`'s own
budget-exhausted-failure handling from Phase 14).

Prompt Cache (docs/02-architecture.md section 101, Phase 17): only
checked/populated when the caller pins an explicit `provider`+`model` —
"useful for benchmarks, automated evaluations, internal testing" per the
architecture doc, i.e. a controlled scenario where the model is a fixed
variable, not a `routing_hint`/default request whose resolved
provider/model can legitimately vary call to call.
"""

import time
import uuid
from dataclasses import asdict

from app.core.cache.keys import hash_text, prompt_cache_key
from app.core.cache.store import CacheStore
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.llm.base import (
    InvalidRequestError,
    LLMMessage,
    ProviderRequestOptions,
)
from app.core.llm.factory import get_provider
from app.core.llm.gateway import AllProvidersFailedError, LLMGateway
from app.core.llm.router import NoMatchingModelError
from app.models.audit_log import AuditLog
from app.models.llm_request import LLMRequest, LLMRequestStatus
from app.models.prompt import PromptStatus
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.llm_request_repository import LLMRequestRepository
from app.schemas.llm import CreateCompletionRequest
from app.services.prompt_service import PromptService


class LLMService:
    def __init__(
        self,
        llm_request_repository: LLMRequestRepository,
        prompt_service: PromptService,
        audit_log_repository: AuditLogRepository,
        gateway: LLMGateway | None = None,
    ):
        self.llm_requests = llm_request_repository
        self.prompts = prompt_service
        self.audit_logs = audit_log_repository
        self.gateway = gateway or LLMGateway()

    async def get_ready_prompt(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        retrieval_id: uuid.UUID,
        prompt_id: uuid.UUID,
    ):
        prompt = await self.prompts.get(document_id, vector_index_id, retrieval_id, prompt_id)
        if prompt.status != PromptStatus.COMPLETED or not prompt.rendered_prompt:
            raise ConflictError(
                "Prompt has not completed successfully; cannot generate a completion from it.",
                code="PROMPT_NOT_COMPLETED",
            )
        return prompt

    async def create_completion(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        retrieval_id: uuid.UUID,
        prompt_id: uuid.UUID,
        payload: CreateCompletionRequest,
        *,
        actor_id: uuid.UUID,
    ) -> LLMRequest:
        prompt = await self.get_ready_prompt(
            document_id, vector_index_id, retrieval_id, prompt_id
        )
        assert prompt.rendered_prompt is not None

        settings = get_settings()
        cache_key: str | None = None
        if settings.cache_enabled and payload.provider and payload.model:
            cache_key = prompt_cache_key(
                prompt.rendered_prompt,
                payload.provider,
                payload.model,
                hash_text(prompt.rendered_context or ""),
            )
            cache_store = CacheStore("prompt", settings.prompt_cache_ttl_seconds)
            cached = await cache_store.get(cache_key)
            if cached is not None:
                llm_request = LLMRequest(
                    prompt_id=prompt_id,
                    provider=payload.provider,
                    model=payload.model,
                    routing_hint=payload.routing_hint,
                    input_text=prompt.rendered_prompt,
                    stream=False,
                    json_mode=payload.json_mode,
                    created_by=actor_id,
                    output_text=cached["output_text"],
                    input_tokens=cached["input_tokens"],
                    output_tokens=cached["output_tokens"],
                    cost_usd=0.0,
                    latency_ms=0,
                    attempted_providers=[
                        {"provider": payload.provider, "model": payload.model, "error": None}
                    ],
                    status=LLMRequestStatus.COMPLETED,
                )
                await self.llm_requests.add(llm_request)
                await self._record_audit(actor_id, llm_request, result="success")
                return llm_request

        llm_request = LLMRequest(
            prompt_id=prompt_id,
            provider=payload.provider or "",
            model=payload.model or "",
            routing_hint=payload.routing_hint,
            input_text=prompt.rendered_prompt,
            stream=False,
            json_mode=payload.json_mode,
            created_by=actor_id,
        )

        messages = [LLMMessage(role="user", content=prompt.rendered_prompt)]
        options = ProviderRequestOptions(json_mode=payload.json_mode)
        started_at = time.monotonic()
        try:
            result, provider_used, model_used, attempts = await self.gateway.generate(
                messages,
                routing_hint=payload.routing_hint,  # type: ignore[arg-type]
                provider=payload.provider,
                model=payload.model,
                options=options,
            )
        except NoMatchingModelError as exc:
            raise ConflictError(str(exc), code="NO_MATCHING_MODEL") from exc
        except AllProvidersFailedError as exc:
            llm_request.status = LLMRequestStatus.FAILED
            llm_request.status_message = str(exc)
            llm_request.attempted_providers = [asdict(a) for a in exc.attempts]
            await self.llm_requests.add(llm_request)
            await self._record_audit(actor_id, llm_request, result="failed")
            return llm_request
        except InvalidRequestError as exc:
            llm_request.status = LLMRequestStatus.FAILED
            llm_request.status_message = exc.message
            llm_request.provider = exc.provider
            await self.llm_requests.add(llm_request)
            await self._record_audit(actor_id, llm_request, result="failed")
            return llm_request

        latency_ms = int((time.monotonic() - started_at) * 1000)
        cost = get_provider(provider_used).cost_estimate(
            result.input_tokens, result.output_tokens, model_used
        )
        llm_request.provider = provider_used
        llm_request.model = model_used
        llm_request.output_text = result.text
        llm_request.input_tokens = result.input_tokens
        llm_request.output_tokens = result.output_tokens
        llm_request.cost_usd = cost.total_usd
        llm_request.latency_ms = latency_ms
        llm_request.attempted_providers = [asdict(a) for a in attempts]
        llm_request.status = LLMRequestStatus.COMPLETED

        if cache_key is not None:
            cache_store = CacheStore("prompt", settings.prompt_cache_ttl_seconds)
            await cache_store.set(
                cache_key,
                {
                    "output_text": result.text,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                },
            )

        await self.llm_requests.add(llm_request)
        await self._record_audit(actor_id, llm_request, result="success")
        return llm_request

    async def list_by_prompt(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        retrieval_id: uuid.UUID,
        prompt_id: uuid.UUID,
    ) -> list[LLMRequest]:
        await self.prompts.get(document_id, vector_index_id, retrieval_id, prompt_id)
        return await self.llm_requests.list_by_prompt(prompt_id)

    async def get(
        self,
        document_id: uuid.UUID,
        vector_index_id: uuid.UUID,
        retrieval_id: uuid.UUID,
        prompt_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> LLMRequest:
        await self.prompts.get(document_id, vector_index_id, retrieval_id, prompt_id)
        llm_request = await self.llm_requests.get_by_id(request_id)
        if llm_request is None or llm_request.prompt_id != prompt_id:
            raise NotFoundError("LLM request not found.", code="LLM_REQUEST_NOT_FOUND")
        return llm_request

    async def _record_audit(
        self, actor_id: uuid.UUID, llm_request: LLMRequest, *, result: str
    ) -> None:
        await self.audit_logs.add(
            AuditLog(
                user_id=actor_id,
                action="llm_request.create",
                resource=str(llm_request.id),
                result=result,
            )
        )
