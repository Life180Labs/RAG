"""Prompt template business logic (docs/05-task.md Phase 14;
docs/02-architecture.md section 79, Prompt Versioning).

Creating a template under a `name` that already has versions always
inserts a new row with `version = max(existing) + 1` — never updates an
existing version in place. This is deliberately unlike Phase 7's
`EmbeddingVersion` (same `provider`+`model` re-run replaces its row):
section 79 requires "Prompt v1/v2/v3" to coexist so experiments can
compare across them, and a past `Prompt` may still reference an older
version's exact text (see `app/models/prompt.py`), which a destructive
update would silently change out from under it.
"""

import uuid

from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.prompt import PromptTemplate
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.prompt_template_repository import PromptTemplateRepository


class PromptTemplateService:
    def __init__(
        self,
        prompt_template_repository: PromptTemplateRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.prompt_templates = prompt_template_repository
        self.audit_logs = audit_log_repository

    async def create_version(
        self,
        *,
        repository_id: uuid.UUID,
        name: str,
        system_prompt: str,
        formatting_instructions: str | None,
        output_schema: dict | None,
        actor_id: uuid.UUID,
    ) -> PromptTemplate:
        next_version = await self.prompt_templates.get_max_version(repository_id, name) + 1
        template = await self.prompt_templates.add(
            PromptTemplate(
                repository_id=repository_id,
                name=name,
                version=next_version,
                system_prompt=system_prompt,
                formatting_instructions=formatting_instructions,
                output_schema=output_schema,
                is_active=True,
                created_by=actor_id,
            )
        )
        await self.audit_logs.add(
            AuditLog(
                user_id=actor_id,
                action="prompt_template.create_version",
                resource=str(template.id),
                result="success",
            )
        )
        return template

    async def list_by_repository(self, repository_id: uuid.UUID) -> list[PromptTemplate]:
        return await self.prompt_templates.list_by_repository(repository_id)

    async def list_versions(self, repository_id: uuid.UUID, name: str) -> list[PromptTemplate]:
        return await self.prompt_templates.list_versions(repository_id, name)

    async def get(self, repository_id: uuid.UUID, template_id: uuid.UUID) -> PromptTemplate:
        template = await self.prompt_templates.get_by_id(template_id)
        if template is None or template.repository_id != repository_id:
            raise NotFoundError("Prompt template not found.", code="PROMPT_TEMPLATE_NOT_FOUND")
        return template

    async def set_active(
        self,
        repository_id: uuid.UUID,
        template_id: uuid.UUID,
        *,
        is_active: bool,
        actor_id: uuid.UUID,
    ) -> PromptTemplate:
        template = await self.get(repository_id, template_id)
        template.is_active = is_active
        await self.audit_logs.add(
            AuditLog(
                user_id=actor_id,
                action="prompt_template.set_active",
                resource=str(template.id),
                result="success",
            )
        )
        return template
