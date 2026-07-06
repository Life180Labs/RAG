"""Per-organization provider API key management.

Upsert semantics on (organization_id, provider), same regeneration-reuses-
id pattern as embedding versions — re-submitting a key for a provider the
org already configured replaces it in place rather than accumulating
duplicate rows. `get_decrypted` is internal-only: never exposed via the
API, used solely by the LLM Gateway / worker wiring to resolve an
org-scoped override in place of the global env-var default.
"""

import uuid

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import decrypt_credential, encrypt_credential
from app.models.audit_log import AuditLog
from app.models.provider_credential import ALLOWED_PROVIDERS, ProviderCredential
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.provider_credential_repository import ProviderCredentialRepository

# The subset of ALLOWED_PROVIDERS the LLM Gateway (backend/app/core/llm/factory.py)
# actually knows how to construct — voyage/jina/cohere/pinecone are worker-side
# (embedding/reranking/vector-index) providers, resolved separately in the worker.
LLM_PROVIDERS = frozenset({"openai", "anthropic", "gemini", "groq", "openrouter"})


class ProviderCredentialService:
    def __init__(
        self,
        provider_credential_repository: ProviderCredentialRepository,
        audit_log_repository: AuditLogRepository,
    ):
        self.credentials = provider_credential_repository
        self.audit_logs = audit_log_repository

    def _validate_provider(self, provider: str) -> str:
        normalized = provider.lower()
        if normalized not in ALLOWED_PROVIDERS:
            raise ForbiddenError(
                f"'{provider}' is not a configurable provider.", code="UNKNOWN_PROVIDER"
            )
        return normalized

    async def _record_audit(
        self, *, user_id: uuid.UUID, action: str, resource: str
    ) -> None:
        await self.audit_logs.add(
            AuditLog(user_id=user_id, action=action, resource=resource, result="success")
        )

    async def upsert(
        self, *, organization_id: uuid.UUID, provider: str, api_key: str, actor_id: uuid.UUID
    ) -> ProviderCredential:
        normalized_provider = self._validate_provider(provider)
        existing = await self.credentials.get_by_org_and_provider(
            organization_id, normalized_provider
        )
        encrypted_key = encrypt_credential(api_key)
        last_four = api_key[-4:]

        if existing is not None:
            existing.encrypted_key = encrypted_key
            existing.last_four = last_four
            existing.updated_by = actor_id
            await self._record_audit(
                user_id=actor_id,
                action="provider_credential.update",
                resource=str(existing.id),
            )
            return existing

        credential = ProviderCredential(
            organization_id=organization_id,
            provider=normalized_provider,
            encrypted_key=encrypted_key,
            last_four=last_four,
            created_by=actor_id,
        )
        await self.credentials.add(credential)
        await self._record_audit(
            user_id=actor_id, action="provider_credential.create", resource=str(credential.id)
        )
        return credential

    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> list[ProviderCredential]:
        return await self.credentials.list_by_organization(organization_id)

    async def delete(
        self, *, organization_id: uuid.UUID, credential_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        credential = await self.credentials.get_by_id(credential_id)
        if credential is None or credential.organization_id != organization_id:
            raise NotFoundError(
                "Provider credential not found.", code="PROVIDER_CREDENTIAL_NOT_FOUND"
            )
        await self.credentials.delete(credential)
        await self._record_audit(
            user_id=actor_id, action="provider_credential.delete", resource=str(credential_id)
        )

    async def get_decrypted(
        self, organization_id: uuid.UUID, provider: str
    ) -> str | None:
        credential = await self.credentials.get_by_org_and_provider(
            organization_id, provider.lower()
        )
        if credential is None:
            return None
        return decrypt_credential(credential.encrypted_key)

    async def get_llm_overrides(self, organization_id: uuid.UUID | None) -> dict[str, str]:
        """Builds the `credential_overrides` dict `LLMGateway.generate`/
        `stream` expect: org-configured LLM provider keys only, decrypted.
        Returns `{}` (never fails) when the org hasn't configured
        anything — the gateway falls back to the env-var default per
        provider exactly as it did before this feature existed."""
        if organization_id is None:
            return {}
        credentials = await self.credentials.list_by_organization(organization_id)
        return {
            c.provider: decrypt_credential(c.encrypted_key)
            for c in credentials
            if c.provider in LLM_PROVIDERS
        }
