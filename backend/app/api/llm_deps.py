"""DI wiring for LLM Gateway routes (docs/05-task.md Phase 15)."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_log_repository
from app.api.document_deps import get_document_repository
from app.api.prompt_deps import get_prompt_service
from app.api.tenancy_deps import get_provider_credential_service
from app.db.session import get_db
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.llm_request_repository import LLMRequestRepository
from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.provider_credential_service import ProviderCredentialService


def get_llm_request_repository(db: AsyncSession = Depends(get_db)) -> LLMRequestRepository:
    return LLMRequestRepository(db)


def get_llm_service(
    llm_request_repository: LLMRequestRepository = Depends(get_llm_request_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
    audit_log_repository: AuditLogRepository = Depends(get_audit_log_repository),
    document_repository: DocumentRepository = Depends(get_document_repository),
    provider_credential_service: ProviderCredentialService = Depends(
        get_provider_credential_service
    ),
) -> LLMService:
    return LLMService(
        llm_request_repository,
        prompt_service,
        audit_log_repository,
        document_repository,
        provider_credential_service,
    )
