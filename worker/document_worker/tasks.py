"""Document processing tasks.

`finalize_upload` is the Phase 4 background step: the backend already
validates and stores the file synchronously (size/extension/password/
virus-scan-stub) before ever enqueuing this task, so its job is just to
confirm the object really landed in storage and flip
UPLOADED -> VALIDATED (or FAILED_VALIDATION if it didn't). On success it
enqueues `parse_document` (Phase 5), continuing the same state machine —
see docs/02-architecture.md section 46.

`parse_document` extracts structured content (docs/02-architecture.md
sections 25/30): PARSING (format-specific parser) -> OCR (only for PDF
pages with no real text layer) -> CLEANING (normalize + strip
headers/footers/page numbers) -> persists the result and metadata to
`document_content`, then advances the document to CHUNKING — the state
that means "ready for the chunking phase" (Phase 6, not yet
implemented), matching the pattern established by VALIDATED meaning
"ready for parsing" in Phase 4.

Raw SQL (not the backend's ORM models) is used deliberately: the worker
and backend are separate deployables with no shared codebase mount, and
these tasks only ever need a few narrow read/write operations — not the
full mapped-model surface.
"""

import json
import statistics
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from common.celery_app import celery_app
from common.config import get_worker_settings
from common.db import SessionLocal
from common.logging import get_logger
from common.storage import get_storage_client, object_exists
from document_worker.parsing import cleaning, ocr
from document_worker.parsing.factory import UnsupportedExtensionError, get_parser
from document_worker.parsing.metadata import compute_metadata

logger = get_logger(__name__)


def _get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _set_status(
    session: Session, document_id: str, status: str, *, message: str | None = None
) -> None:
    session.execute(
        text(
            "UPDATE documents SET status = :status, status_message = :message, "
            "updated_at = :now WHERE id = :id"
        ),
        {"status": status, "message": message, "now": datetime.now(UTC), "id": document_id},
    )
    session.commit()


@celery_app.task(name="document_worker.finalize_upload")
def finalize_upload(document_id: str) -> dict:
    # Uses the "default" queue like every other task today. Dedicated
    # per-worker-type queues (docs/02-architecture.md section 182) are a
    # deployment-time change (`celery worker -Q documents`), not a code
    # change — introduce them once independent scaling is actually needed.
    settings = get_worker_settings()

    with SessionLocal() as session:
        row = session.execute(
            text("SELECT storage_key FROM documents WHERE id = :id"), {"id": document_id}
        ).first()

        if row is None:
            logger.warning("finalize_upload_document_missing", document_id=document_id)
            return {"status": "skipped", "reason": "document_not_found"}

        storage_key = row.storage_key

        if object_exists(settings.minio_bucket, storage_key):
            _set_status(session, document_id, "VALIDATED")
            result = {"status": "validated"}
        else:
            _set_status(
                session,
                document_id,
                "FAILED_VALIDATION",
                message="Uploaded file could not be found in storage.",
            )
            result = {"status": "failed_validation"}

    if result["status"] == "validated":
        parse_document.delay(document_id)

    logger.info("finalize_upload_completed", document_id=document_id, **result)
    return result


@celery_app.task(
    name="document_worker.parse_document",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def parse_document(document_id: str) -> dict:
    """Retries (up to 3x, exponential backoff) are Celery's `autoretry_for`
    re-running this task from scratch on any exception. There's no
    separate dead-letter queue infrastructure — once retries are
    exhausted, the persisted FAILED_PARSE/FAILED_OCR status *is* the
    dead-letter record, consistent with how Phase 4 already surfaces
    failures via `documents.status`/`status_message` rather than a
    parallel logging system."""
    settings = get_worker_settings()

    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT filename, storage_key, current_version FROM documents WHERE id = :id"
            ),
            {"id": document_id},
        ).first()

        if row is None:
            logger.warning("parse_document_missing", document_id=document_id)
            return {"status": "skipped", "reason": "document_not_found"}

        filename, storage_key, version = row.filename, row.storage_key, row.current_version
        extension = _get_extension(filename)

        _set_status(session, document_id, "PARSING")

        try:
            parse_fn, parser_name = get_parser(extension)
        except UnsupportedExtensionError as exc:
            _set_status(session, document_id, "FAILED_PARSE", message=str(exc)[:500])
            return {"status": "failed_parse", "reason": str(exc)}

        client = get_storage_client()
        response = client.get_object(settings.minio_bucket, storage_key)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()

        try:
            blocks, page_count = parse_fn(content)
        except Exception as exc:
            message = f"Parsing failed: {exc}"[:500]
            _set_status(session, document_id, "FAILED_PARSE", message=message)
            raise

        ocr_used = False
        ocr_confidence_values: list[float] = []

        if extension == "pdf" and page_count:
            page_texts: dict[int, str] = dict.fromkeys(range(1, page_count + 1), "")
            for block in blocks:
                if block["page"] is not None and block["type"] != "image":
                    page_texts[block["page"]] += block["text"]

            pages_needing_ocr = [p for p, t in page_texts.items() if ocr.page_needs_ocr(t)]

            if pages_needing_ocr:
                _set_status(session, document_id, "OCR")
                try:
                    ocr_results = ocr.ocr_pdf_pages(content, pages_needing_ocr)
                except Exception as exc:
                    message = f"OCR failed: {exc}"[:500]
                    _set_status(session, document_id, "FAILED_OCR", message=message)
                    raise

                blocks = [b for b in blocks if b["page"] not in ocr_results]
                for page_number, (ocr_text, confidence) in ocr_results.items():
                    if ocr_text.strip():
                        blocks.append(
                            {
                                "type": "paragraph",
                                "text": ocr_text,
                                "level": None,
                                "page": page_number,
                            }
                        )
                    ocr_confidence_values.append(confidence)
                ocr_used = True

        _set_status(session, document_id, "CLEANING")

        cleaned_blocks = cleaning.clean_blocks(blocks)
        meta = compute_metadata(cleaned_blocks, page_count)
        avg_confidence = (
            statistics.mean(ocr_confidence_values) if ocr_confidence_values else None
        )

        session.execute(
            text(
                "INSERT INTO document_content (id, document_id, version, raw_text, "
                "structured_content, language, page_count, word_count, character_count, "
                "reading_time_seconds, parser_used, ocr_used, ocr_confidence, created_at, "
                "updated_at) "
                "VALUES (:id, :document_id, :version, :raw_text, "
                "CAST(:structured_content AS jsonb), :language, :page_count, :word_count, "
                ":character_count, :reading_time_seconds, :parser_used, :ocr_used, "
                ":ocr_confidence, :now, :now) "
                "ON CONFLICT (document_id) DO UPDATE SET "
                "version = EXCLUDED.version, raw_text = EXCLUDED.raw_text, "
                "structured_content = EXCLUDED.structured_content, "
                "language = EXCLUDED.language, page_count = EXCLUDED.page_count, "
                "word_count = EXCLUDED.word_count, character_count = EXCLUDED.character_count, "
                "reading_time_seconds = EXCLUDED.reading_time_seconds, "
                "parser_used = EXCLUDED.parser_used, ocr_used = EXCLUDED.ocr_used, "
                "ocr_confidence = EXCLUDED.ocr_confidence, updated_at = EXCLUDED.updated_at"
            ),
            {
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "version": version,
                "raw_text": meta["raw_text"],
                "structured_content": json.dumps(cleaned_blocks),
                "language": meta["language"],
                "page_count": meta["page_count"],
                "word_count": meta["word_count"],
                "character_count": meta["character_count"],
                "reading_time_seconds": meta["reading_time_seconds"],
                "parser_used": parser_name,
                "ocr_used": ocr_used,
                "ocr_confidence": avg_confidence,
                "now": datetime.now(UTC),
            },
        )
        session.commit()

        # `documents.language`/`.page_count` mirror the values just written
        # to `document_content`, so callers reading the document itself
        # (e.g. the API's DocumentRead) don't need a separate join/query
        # to see them — see backend/app/models/document.py.
        session.execute(
            text(
                "UPDATE documents SET language = :language, page_count = :page_count, "
                "updated_at = :now WHERE id = :id"
            ),
            {
                "language": meta["language"],
                "page_count": meta["page_count"],
                "now": datetime.now(UTC),
                "id": document_id,
            },
        )
        session.commit()

        _set_status(session, document_id, "CHUNKING")

    logger.info(
        "parse_document_completed",
        document_id=document_id,
        parser=parser_name,
        ocr_used=ocr_used,
    )
    return {"status": "chunking", "parser": parser_name, "ocr_used": ocr_used}
