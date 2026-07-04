"""Chunk generation tasks (docs/05-task.md Phase 6; docs/02-architecture.md
sections 31-39).

`chunk_document` picks up where `document_worker.parse_document` leaves
off: it reads the already-parsed `structured_content` (Phase 5), runs
the selected chunker, validates the results, and persists a
`document_chunk_sets` row plus its `chunks`. On success the document
advances CHUNKING -> EMBEDDING — the "ready for the next phase" marker,
same pattern as VALIDATED meaning "ready for parsing" in Phase 4 and
CHUNKING itself meaning "ready for chunking" at the end of Phase 5.

Re-running the *same* strategy for a document replaces its chunk set
(`ON CONFLICT (document_id, strategy)`) rather than accumulating
duplicates; running a *different* strategy adds a second, independent
set — which is what makes side-by-side strategy comparison possible.

Raw SQL is used deliberately, same as document_worker — this worker
package is independently deployable and doesn't import document_worker
or the backend's ORM models; it only knows the columns it actually reads
and writes.
"""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from chunk_worker.chunking.adaptive import chunk_adaptive
from chunk_worker.chunking.factory import default_config, get_chunker
from chunk_worker.chunking.text_utils import join_blocks_with_spans
from chunk_worker.chunking.validation import validate_chunks
from common.celery_app import celery_app
from common.db import SessionLocal
from common.logging import get_logger

logger = get_logger(__name__)

DEFAULT_STRATEGY = "recursive"


def _set_document_status(
    session, document_id: str, status: str, message: str | None = None
) -> None:
    session.execute(
        text(
            "UPDATE documents SET status = :status, status_message = :message, "
            "updated_at = :now WHERE id = :id"
        ),
        {"status": status, "message": message, "now": datetime.now(UTC), "id": document_id},
    )
    session.commit()


@celery_app.task(
    name="chunk_worker.chunk_document",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def chunk_document(document_id: str, strategy: str | None = None) -> dict:
    with SessionLocal() as session:
        document_row = session.execute(
            text("SELECT repository_id, current_version FROM documents WHERE id = :id"),
            {"id": document_id},
        ).first()
        if document_row is None:
            logger.warning("chunk_document_missing", document_id=document_id)
            return {"status": "skipped", "reason": "document_not_found"}

        content_row = session.execute(
            text(
                "SELECT structured_content, version FROM document_content "
                "WHERE document_id = :id"
            ),
            {"id": document_id},
        ).first()
        if content_row is None:
            message = "No parsed content found for this document."
            _set_document_status(session, document_id, "FAILED_CHUNK", message)
            logger.warning("chunk_document_no_content", document_id=document_id)
            return {"status": "failed_chunk", "reason": message}

        repository_row = session.execute(
            text("SELECT default_chunk_strategy FROM repositories WHERE id = :id"),
            {"id": document_row.repository_id},
        ).first()

        requested_strategy = (
            strategy
            or (repository_row.default_chunk_strategy if repository_row else None)
            or DEFAULT_STRATEGY
        )

        try:
            blocks = content_row.structured_content
            raw_text, spans = join_blocks_with_spans(blocks)

            if requested_strategy == "adaptive":
                chunks, resolved_strategy, resolved_config = chunk_adaptive(raw_text, spans, {})
                config = {"resolved_strategy": resolved_strategy, **resolved_config}
            else:
                config = default_config(requested_strategy)
                chunker = get_chunker(requested_strategy)
                chunks = chunker(raw_text, spans, config)

            validate_chunks(chunks)
        except Exception as exc:
            message = f"Chunking failed: {exc}"[:500]
            _set_document_status(session, document_id, "FAILED_CHUNK", message)
            raise

        ready_count = sum(1 for c in chunks if c["status"] == "ready")

        old_set_row = session.execute(
            text(
                "SELECT id, chunk_count FROM document_chunk_sets "
                "WHERE document_id = :document_id AND strategy = :strategy"
            ),
            {"document_id": document_id, "strategy": requested_strategy},
        ).first()
        old_ready_count = old_set_row.chunk_count if old_set_row else 0
        # Regenerating reuses the existing chunk_set id rather than
        # swapping in a new one — chunks FK-reference chunk_set_id, so
        # changing the parent's primary key while children still point at
        # the old value would violate the FK constraint (there's no ON
        # UPDATE CASCADE here, deliberately, since ids should be stable).
        chunk_set_id = str(old_set_row.id) if old_set_row is not None else str(uuid.uuid4())

        # Delete this set's previous chunks *before* re-inserting — both
        # to free the FK reference above and because uq_chunk_set_index
        # would otherwise collide with the new rows' chunk_index values.
        if old_set_row is not None:
            session.execute(
                text("DELETE FROM chunks WHERE chunk_set_id = :chunk_set_id"),
                {"chunk_set_id": chunk_set_id},
            )

        session.execute(
            text(
                "INSERT INTO document_chunk_sets "
                "(id, document_id, version, strategy, config, status, status_message, "
                "chunk_count, created_at, updated_at) "
                "VALUES (:id, :document_id, :version, :strategy, CAST(:config AS jsonb), "
                "'READY', NULL, :chunk_count, :now, :now) "
                "ON CONFLICT (document_id, strategy) DO UPDATE SET "
                "version = EXCLUDED.version, config = EXCLUDED.config, "
                "status = EXCLUDED.status, status_message = EXCLUDED.status_message, "
                "chunk_count = EXCLUDED.chunk_count, updated_at = EXCLUDED.updated_at"
            ),
            {
                "id": chunk_set_id,
                "document_id": document_id,
                "version": content_row.version,
                "strategy": requested_strategy,
                "config": json.dumps(config),
                "chunk_count": ready_count,
                "now": datetime.now(UTC),
            },
        )

        chunk_ids = [str(uuid.uuid4()) for _ in chunks]
        for index, (chunk, chunk_id) in enumerate(zip(chunks, chunk_ids, strict=True)):
            parent_ref = chunk.get("parent_ref")
            parent_chunk_id = chunk_ids[parent_ref] if parent_ref is not None else None
            session.execute(
                text(
                    "INSERT INTO chunks "
                    "(id, chunk_set_id, parent_chunk_id, chunk_index, text, char_start, "
                    "char_end, token_count, page, heading, status, status_message) "
                    "VALUES (:id, :chunk_set_id, :parent_chunk_id, :chunk_index, :text, "
                    ":char_start, :char_end, :token_count, :page, :heading, :status, "
                    ":status_message)"
                ),
                {
                    "id": chunk_id,
                    "chunk_set_id": chunk_set_id,
                    "parent_chunk_id": parent_chunk_id,
                    "chunk_index": index,
                    "text": chunk["text"],
                    "char_start": chunk["char_start"],
                    "char_end": chunk["char_end"],
                    "token_count": chunk["token_count"],
                    "page": chunk["page"],
                    "heading": chunk["heading"],
                    "status": chunk["status"].upper(),
                    "status_message": chunk["status_message"],
                },
            )
        session.commit()

        session.execute(
            text(
                "UPDATE repositories SET chunk_count = GREATEST(0, chunk_count - :old + :new), "
                "updated_at = :now WHERE id = :id"
            ),
            {
                "old": old_ready_count,
                "new": ready_count,
                "now": datetime.now(UTC),
                "id": document_row.repository_id,
            },
        )
        session.commit()

        _set_document_status(session, document_id, "EMBEDDING")

    logger.info(
        "chunk_document_completed",
        document_id=document_id,
        strategy=requested_strategy,
        chunk_count=ready_count,
    )
    return {"status": "embedding", "strategy": requested_strategy, "chunk_count": ready_count}
