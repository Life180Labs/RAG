"""DI wiring for conversation/memory routes (docs/05-task.md Phase 16)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository
from app.api.llm_deps import get_llm_service
from app.api.prompt_deps import get_prompt_service, get_prompt_template_repository
from app.api.retrieval_deps import get_retrieval_service
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.conversation_repository import (
    ConversationMemoryRepository,
    ConversationRepository,
    ConversationSummaryRepository,
    MessageRepository,
)
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.services.conversation_service import ConversationService
from app.services.llm_service import LLMService
from app.services.memory_service import MemoryService
from app.services.prompt_service import PromptService
from app.services.retrieval_service import RetrievalService


def get_conversation_repository(db: AsyncSession = Depends(get_db)) -> ConversationRepository:
    return ConversationRepository(db)


def get_message_repository(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


def get_conversation_summary_repository(
    db: AsyncSession = Depends(get_db),
) -> ConversationSummaryRepository:
    return ConversationSummaryRepository(db)


def get_conversation_memory_repository(
    db: AsyncSession = Depends(get_db),
) -> ConversationMemoryRepository:
    return ConversationMemoryRepository(db)


def get_conversation_service(
    conversation_repository: ConversationRepository = Depends(get_conversation_repository),
    message_repository: MessageRepository = Depends(get_message_repository),
    summary_repository: ConversationSummaryRepository = Depends(
        get_conversation_summary_repository
    ),
    memory_repository: ConversationMemoryRepository = Depends(
        get_conversation_memory_repository
    ),
    prompt_template_repository: PromptTemplateRepository = Depends(
        get_prompt_template_repository
    ),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> ConversationService:
    return ConversationService(
        conversation_repository,
        message_repository,
        summary_repository,
        memory_repository,
        prompt_template_repository,
        retrieval_service,
        prompt_service,
        llm_service,
        audit_log_repository,
    )


def get_memory_service(
    memory_repository: ConversationMemoryRepository = Depends(
        get_conversation_memory_repository
    ),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> MemoryService:
    return MemoryService(memory_repository, audit_log_repository)
