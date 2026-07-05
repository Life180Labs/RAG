"""LLM Gateway endpoints (docs/05-task.md Phase 15).

Model registry/health endpoints (`/llm/models*`) are authenticated but
not tenant-scoped — they describe the gateway itself, not any
repository's data, the same way `/health/*` needs no RBAC.

Completions are nested under a prompt (document/vector-index/retrieval/
prompt chain), same VIEWER+ pattern as reading a `Prompt` — generating a
completion from an already-built, already-citation-grounded prompt is a
read-oriented action over data that already exists, not a mutation of it.

The streaming route is a WebSocket, not SSE (docs/02-architecture.md
section 87's "LLM -> Gateway -> WebSocket -> Frontend" diagram;
docs/04-api-spec.md section 27 calls out WebSocket specifically for
"streaming LLM responses"). Browsers' native WebSocket API cannot set a
custom `Authorization` header on the handshake request, so auth instead
happens via the first message the client sends after the socket opens
(`{"token": "<jwt>"}`) — never via a `?token=` query string, which would
leak the token into server/proxy access logs.
"""

import time
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository, get_current_user
from app.api.document_deps import (
    DocumentAccess,
    get_document_repository,
    require_document_role,
)
from app.api.llm_deps import get_llm_service
from app.api.prompt_deps import (
    get_prompt_repository,
    get_prompt_template_repository,
)
from app.api.retrieval_deps import (
    get_retrieval_repository,
    get_retrieval_result_repository,
)
from app.api.vector_index_deps import get_vector_index_repository
from app.core.exceptions import ConflictError
from app.core.llm.base import InvalidRequestError, LLMMessage, ProviderRequestOptions
from app.core.llm.factory import get_provider, is_configured
from app.core.llm.gateway import AllProvidersFailedError, LLMGateway
from app.core.llm.registry import list_models
from app.core.llm.router import NoMatchingModelError
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.db.session import get_db
from app.models.llm_request import LLMRequest, LLMRequestStatus
from app.models.membership import MemberRole, role_meets_minimum
from app.models.user import User
from app.repositories.llm_request_repository import LLMRequestRepository
from app.repositories.membership_repository import RepositoryMemberRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import SuccessResponse
from app.schemas.llm import (
    CreateCompletionRequest,
    LLMRequestRead,
    ModelSpecRead,
    ProviderHealth,
)
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService

router = APIRouter(tags=["llm"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@router.get("/llm/models", response_model=SuccessResponse[list[ModelSpecRead]])
async def list_models_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[list[ModelSpecRead]]:
    return SuccessResponse(
        data=[ModelSpecRead.model_validate(m.__dict__) for m in list_models()],
        request_id=_request_id(request),
    )


@router.get(
    "/llm/models/{provider}/health",
    response_model=SuccessResponse[ProviderHealth],
)
async def provider_health(
    provider: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SuccessResponse[ProviderHealth]:
    configured = is_configured(provider)
    healthy = await get_provider(provider).health_check() if configured else False
    return SuccessResponse(
        data=ProviderHealth(provider=provider, configured=configured, healthy=healthy),
        request_id=_request_id(request),
    )


_COMPLETIONS_PATH = (
    "/documents/{document_id}/vector-indexes/{vector_index_id}/retrievals/{retrieval_id}"
    "/prompts/{prompt_id}/completions"
)


@router.post(_COMPLETIONS_PATH, response_model=SuccessResponse[LLMRequestRead])
async def create_completion(
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    prompt_id: uuid.UUID,
    payload: CreateCompletionRequest,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: LLMService = Depends(get_llm_service),
) -> SuccessResponse[LLMRequestRead]:
    llm_request = await service.create_completion(
        access.document.id,
        vector_index_id,
        retrieval_id,
        prompt_id,
        payload,
        actor_id=access.membership.user_id,
    )
    return SuccessResponse(
        data=LLMRequestRead.model_validate(llm_request), request_id=_request_id(request)
    )


@router.get(_COMPLETIONS_PATH, response_model=SuccessResponse[list[LLMRequestRead]])
async def list_completions(
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    prompt_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: LLMService = Depends(get_llm_service),
) -> SuccessResponse[list[LLMRequestRead]]:
    llm_requests = await service.list_by_prompt(
        access.document.id, vector_index_id, retrieval_id, prompt_id
    )
    return SuccessResponse(
        data=[LLMRequestRead.model_validate(r) for r in llm_requests],
        request_id=_request_id(request),
    )


@router.get(f"{_COMPLETIONS_PATH}/{{request_id}}", response_model=SuccessResponse[LLMRequestRead])
async def get_completion(
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    prompt_id: uuid.UUID,
    request_id: uuid.UUID,
    request: Request,
    access: DocumentAccess = Depends(require_document_role(MemberRole.VIEWER)),
    service: LLMService = Depends(get_llm_service),
) -> SuccessResponse[LLMRequestRead]:
    llm_request = await service.get(
        access.document.id, vector_index_id, retrieval_id, prompt_id, request_id
    )
    return SuccessResponse(
        data=LLMRequestRead.model_validate(llm_request), request_id=_request_id(request)
    )


def _build_llm_service(db: AsyncSession) -> LLMService:
    retrieval_service = RetrievalService(
        get_retrieval_repository(db),
        get_retrieval_result_repository(db),
        get_vector_index_repository(db),
        get_audit_log_repository(db),
    )
    prompt_service = PromptService(
        get_prompt_repository(db),
        get_prompt_template_repository(db),
        retrieval_service,
        get_audit_log_repository(db),
    )
    return LLMService(
        LLMRequestRepository(db), prompt_service, get_audit_log_repository(db)
    )


@router.websocket(f"{_COMPLETIONS_PATH}/stream")
async def stream_completion(
    websocket: WebSocket,
    document_id: uuid.UUID,
    vector_index_id: uuid.UUID,
    retrieval_id: uuid.UUID,
    prompt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await websocket.accept()
    try:
        auth_message = await websocket.receive_json()
    except (WebSocketDisconnect, ValueError):
        return

    token = auth_message.get("token")
    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return
    try:
        token_payload = decode_token(token, TokenType.ACCESS)
    except InvalidTokenError:
        await websocket.close(code=4401, reason="Invalid or expired access token")
        return

    user = await UserRepository(db).get_by_id(uuid.UUID(token_payload["sub"]))
    if user is None or not user.is_active:
        await websocket.close(code=4401, reason="Invalid or expired access token")
        return

    document = await get_document_repository(db).get_active_by_id(document_id)
    if document is None:
        await websocket.close(code=4404, reason="Document not found")
        return
    membership = await RepositoryMemberRepository(db).get_membership(
        document.repository_id, user.id
    )
    if membership is None or not role_meets_minimum(membership.role, MemberRole.VIEWER):
        await websocket.close(code=4403, reason="Forbidden")
        return

    service = _build_llm_service(db)
    try:
        prompt = await service.get_ready_prompt(
            document.id, vector_index_id, retrieval_id, prompt_id
        )
    except ConflictError as exc:
        await websocket.send_json({"type": "error", "message": exc.message})
        await websocket.close(code=4409, reason="Prompt not completed")
        return

    payload = CreateCompletionRequest(
        provider=auth_message.get("provider"),
        model=auth_message.get("model"),
        routing_hint=auth_message.get("routing_hint"),
        json_mode=bool(auth_message.get("json_mode", False)),
    )

    llm_request = LLMRequest(
        prompt_id=prompt_id,
        provider=payload.provider or "",
        model=payload.model or "",
        routing_hint=payload.routing_hint,
        input_text=prompt.rendered_prompt or "",
        stream=True,
        json_mode=payload.json_mode,
        created_by=user.id,
    )

    gateway = LLMGateway()
    messages = [LLMMessage(role="user", content=prompt.rendered_prompt or "")]
    options = ProviderRequestOptions(json_mode=payload.json_mode)
    output_text = ""
    started_at = time.monotonic()
    try:
        async for chunk, provider_used, model_used, attempts in gateway.stream(
            messages,
            routing_hint=payload.routing_hint,  # type: ignore[arg-type]
            provider=payload.provider,
            model=payload.model,
            options=options,
        ):
            if chunk.delta_text:
                output_text += chunk.delta_text
                await websocket.send_json({"type": "delta", "text": chunk.delta_text})
            if chunk.done:
                llm_request.provider = provider_used
                llm_request.model = model_used
                llm_request.output_text = output_text
                llm_request.input_tokens = chunk.input_tokens or 0
                llm_request.output_tokens = chunk.output_tokens or 0
                llm_request.latency_ms = int((time.monotonic() - started_at) * 1000)
                llm_request.attempted_providers = [asdict(a) for a in attempts]
                llm_request.status = LLMRequestStatus.COMPLETED
                try:
                    cost = get_provider(provider_used).cost_estimate(
                        llm_request.input_tokens, llm_request.output_tokens, model_used
                    )
                    llm_request.cost_usd = cost.total_usd
                except KeyError:
                    pass
                await websocket.send_json(
                    {
                        "type": "done",
                        "provider": provider_used,
                        "model": model_used,
                        "input_tokens": llm_request.input_tokens,
                        "output_tokens": llm_request.output_tokens,
                    }
                )
    except (NoMatchingModelError, AllProvidersFailedError, InvalidRequestError) as exc:
        llm_request.status = LLMRequestStatus.FAILED
        llm_request.status_message = str(exc)
        if isinstance(exc, AllProvidersFailedError):
            llm_request.attempted_providers = [asdict(a) for a in exc.attempts]
        await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        await service.llm_requests.add(llm_request)
        await db.commit()
        await websocket.close()
