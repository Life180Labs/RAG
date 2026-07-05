"""Conversation Memory models (docs/05-task.md Phase 16;
docs/02-architecture.md sections 95-98).

Four tables, matching the phase's task.md checklist exactly:

**`conversations`** is scoped to a `(document_id, vector_index_id)` pair — the same granularity
`Retrieval` already uses (docs/02-architecture.md section 96's "Conversation State" lists
"Retrieved Context" and "Selected Model" as per-session state, but every retrieval in this
codebase already targets exactly one embedding version's index, per `embedding.py`'s
zero-padding-makes-cross-version-comparison-meaningless constraint) — a conversation is a
multi-turn chat over one document's index, not a cross-repository search. Hard-deleted (no
`SoftDeleteMixin`): unlike `Document`/`Repository`, a conversation isn't a browsable historical
record the rest of the tenancy hierarchy depends on: `ON DELETE CASCADE` from `messages`/
`conversation_summaries` is exactly what "Delete Conversation" (task.md API deliverable) means.

**`messages`** is one row per turn (`role` = user or assistant), not one row per exchange — the
standard chat-log shape. Only assistant messages populate `retrieval_id`/`prompt_id`/
`llm_request_id` (`ON DELETE SET NULL` — a message stays readable even if, say, its retrieval is
later cascade-deleted through a much less likely path), tying each answer back to the exact
Phase 9/14/15 rows that produced it — the same "every stage adds its own inspectable field"
pattern this codebase has followed since Phase 10.

**`conversation_summaries`** is additive, not destructive-upsert (mirrors `PromptTemplate`'s
versioning rationale from Phase 14): each summarization pass inserts a new row rather than
overwriting the last one, so the summarization history itself stays auditable.
`covers_up_to_message_id` marks the last raw message folded into that summary, so the next
summarization pass (or prompt-building context assembly) knows where the "not yet summarized"
tail begins.

**`conversation_memory`** is Long-Term Memory (section 95) — persisted *across* conversations,
keyed by `(user_id, repository_id)` rather than by one conversation. Concretely implemented here:
`custom_instructions` (folded into future turns' system prompt) and `preferences` (JSONB,
free-form). "Frequently Accessed Repositories" is deliberately **not** a stored ranking — it's
derived by querying `conversations` grouped by repository, the same way this codebase prefers a
live query over a redundant cached counter wherever the source data already exists. "Saved
Searches" is not implemented this phase — no other part of this app has a "saved search" concept
yet to hang it off of; documented as a real, honest gap rather than a speculative half-feature.
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversations"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    vector_index_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vector_indexes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retrievals.id", ondelete="SET NULL"), nullable=True
    )
    prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="SET NULL"), nullable=True
    )
    llm_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("llm_requests.id", ondelete="SET NULL"), nullable=True
    )


class ConversationSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversation_summaries"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    covers_message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    covers_up_to_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )


class ConversationMemory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversation_memory"
    __table_args__ = (
        UniqueConstraint("user_id", "repository_id", name="uq_conversation_memory_user_repository"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    custom_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
