"""LLM request models (docs/05-task.md Phase 15; docs/02-architecture.md
sections 82-90).

`LLMRequest` is one completion call through the gateway — always tied to
a `prompt_id` (Phase 14's `Prompt`, `ON DELETE CASCADE`), since the
gateway's actual use in this app is "send an already-built, already-
grounded-in-citations Prompt to an LLM and get an answer", not a
general-purpose chat API with no tenant scope. This also keeps RBAC
consistent: access to a completion is governed by the same
document/vector-index/retrieval/prompt chain every other Phase 9-14
resource already uses, rather than inventing a parallel ungoverned
resource.

`attempted_providers` (JSONB) records the gateway's retry/fallback trail
(docs/02-architecture.md section 86) — one entry per provider actually
tried, with its error if it failed — so a completion that succeeded on
the third provider in the fallback chain stays fully auditable rather
than silently looking identical to one that succeeded on the first try.

Cost/latency (sections 89-90) are first-class columns, matching this
codebase's convention of dedicated columns for anything the frontend
charts directly (e.g. `retrievals.avg_similarity`, `prompts.total_tokens`)
rather than a JSONB blob.
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMRequestStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "llm_requests"

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Not a Postgres enum — new providers are expected over time (matching
    # Chunk.strategy/Embedding.provider's rationale for the same choice).
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    routing_hint: Mapped[str | None] = mapped_column(String(20), nullable=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    json_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempted_providers: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[LLMRequestStatus] = mapped_column(
        Enum(LLMRequestStatus, name="llm_request_status"),
        nullable=False,
        default=LLMRequestStatus.PENDING,
    )
    status_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
