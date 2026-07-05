"""Prompt models (docs/05-task.md Phase 14; docs/02-architecture.md
sections 76-80: Token Budget Manager, Context Window Builder, Prompt
Builder, Prompt Versioning, Citation Engine).

Phase 14 is the first phase since Phase 10 to introduce a genuinely new
resource type rather than extending `Retrieval`/`RetrievalResult` —
prompt construction is conceptually downstream of retrieval (it consumes
a completed `Retrieval`'s ranked results), not another mode of it.

`PromptTemplate` is repository-scoped (docs/02-architecture.md section
79 requires "Prompt v1/v2/v3" to coexist for experiment comparison), so
unlike `EmbeddingVersion` (which replaces its row in place on
same-provider+model re-run), a new template version is always a new row:
uniqueness is `(repository_id, name, version)`, never `(repository_id,
name)`. `is_active` marks whether a version is still offered when
building new prompts; past `Prompt` rows keep referencing archived
versions unaffected, since prompt generation must stay reproducible
(this phase's Acceptance Criteria) even after a template is superseded.

`Prompt` is one built prompt — always tied to a single completed
`Retrieval` (the Context Window Builder pipeline in section 77 explains
"the final context is assembled after reranking", i.e. from that
retrieval's already-ranked `RetrievalResult` rows). `prompt_template_id`
is nullable to allow building an ad-hoc prompt without saving a
template first, but the resolved text is always snapshotted onto the
`Prompt` row itself (`rendered_system_prompt`/`rendered_context`/
`rendered_prompt`) rather than re-resolved from the template at read
time — a template can gain new versions later, and reproducibility
requires the *exact* text used at build time to stay stable regardless.

Token accounting mirrors docs/02-architecture.md section 76's budget
allocation (System Prompt / Conversation / Retrieved Context / User
Query / Response Budget) as separate columns rather than one JSONB blob,
matching the existing convention of first-class columns for anything the
frontend needs to chart/inspect directly (see `Retrieval.avg_similarity`
etc.). `conversation_tokens` is always 0 in this phase — persistent
conversation memory is Phase 16 (`docs/05-task.md`), which does not exist
yet; the column exists now so Phase 16 can populate it without another
migration, exactly like `Retrieval.detected_metadata_filter` anticipated
Phase 11 while phases 9-10 left it null.

`citations` (Citation Engine, section 80) is JSONB — a list of
`{chunk_id, document_id, page, section, confidence}` objects — because
its shape is a derived, display-only projection of data already living
in normalized form on `Chunk`/`Document`/`RetrievalResult`; there is no
independent citation identity to key a join table on.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PromptStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prompt_templates"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "name", "version", name="uq_prompt_template_repository_name_version"
        ),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    formatting_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Prompt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "prompts"

    retrieval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrievals.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    model_context_window: Mapped[int] = mapped_column(Integer, nullable=False, default=8192)
    system_prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversation_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    query_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_budget_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rendered_system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendered_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[PromptStatus] = mapped_column(
        Enum(PromptStatus, name="prompt_status"), nullable=False, default=PromptStatus.PENDING
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
