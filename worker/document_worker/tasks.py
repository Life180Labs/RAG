"""Document processing tasks.

`finalize_upload` is the Phase 4 background step: the backend already
validates and stores the file synchronously (size/extension/password/
virus-scan-stub) before ever enqueuing this task, so its job is just to
confirm the object really landed in storage and flip
UPLOADED -> VALIDATED (or FAILED_VALIDATION if it didn't). Parsing/OCR/
chunking/embedding continue this same state machine in later phases —
see docs/02-architecture.md section 46.

Raw SQL (not the backend's ORM models) is used deliberately: the worker
and backend are separate deployables with no shared codebase mount, and
this task only ever needs two narrow operations (read a few columns,
update a status) — not the full mapped-model surface.
"""

from datetime import UTC, datetime

from sqlalchemy import text

from common.celery_app import celery_app
from common.config import get_worker_settings
from common.db import SessionLocal
from common.logging import get_logger
from common.storage import object_exists

logger = get_logger(__name__)


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
        now = datetime.now(UTC)

        if object_exists(settings.minio_bucket, storage_key):
            session.execute(
                text(
                    "UPDATE documents SET status = 'VALIDATED', status_message = NULL, "
                    "updated_at = :now WHERE id = :id"
                ),
                {"now": now, "id": document_id},
            )
            result = {"status": "validated"}
        else:
            session.execute(
                text(
                    "UPDATE documents SET status = 'FAILED_VALIDATION', "
                    "status_message = :message, updated_at = :now WHERE id = :id"
                ),
                {
                    "message": "Uploaded file could not be found in storage.",
                    "now": now,
                    "id": document_id,
                },
            )
            result = {"status": "failed_validation"}

        session.commit()

    logger.info("finalize_upload_completed", document_id=document_id, **result)
    return result
