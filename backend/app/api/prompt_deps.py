"""DI wiring for prompt-template (repository-scoped) and prompt
(retrieval-scoped) routes."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository
from app.api.retrieval_deps import get_retrieval_service
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prompt_repository import PromptRepository
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.services.prompt_service import PromptService
from app.services.prompt_template_service import PromptTemplateService
from app.services.retrieval_service import RetrievalService


def get_prompt_template_repository(
    db: AsyncSession = Depends(get_db),
) -> PromptTemplateRepository:
    return PromptTemplateRepository(db)


def get_prompt_repository(db: AsyncSession = Depends(get_db)) -> PromptRepository:
    return PromptRepository(db)


def get_prompt_template_service(
    prompt_template_repository: PromptTemplateRepository = Depends(
        get_prompt_template_repository
    ),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> PromptTemplateService:
    return PromptTemplateService(prompt_template_repository, audit_log_repository)


def get_prompt_service(
    prompt_repository: PromptRepository = Depends(get_prompt_repository),
    prompt_template_repository: PromptTemplateRepository = Depends(
        get_prompt_template_repository
    ),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
) -> PromptService:
    return PromptService(
        prompt_repository, prompt_template_repository, retrieval_service, audit_log_repository
    )
