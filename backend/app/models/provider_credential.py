import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# Not an enum (unlike e.g. invitations.status): matches the plain-varchar
# `provider` columns already used on embeddings/vector_indexes/retrievals,
# so adding a 10th provider later never needs an enum migration. Validated
# against ALLOWED_PROVIDERS in the Pydantic schema instead.
ALLOWED_PROVIDERS = frozenset(
    {
        "openai",
        "anthropic",
        "gemini",
        "groq",
        "openrouter",
        "voyage",
        "jina",
        "cohere",
        "pinecone",
    }
)


class ProviderCredential(Base, UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin):
    __tablename__ = "provider_credentials"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", name="uq_provider_credential_org_provider"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored alongside the ciphertext so the UI can render "sk-...ab12"
    # without ever decrypting the key just to display it.
    last_four: Mapped[str] = mapped_column(String(4), nullable=False)
