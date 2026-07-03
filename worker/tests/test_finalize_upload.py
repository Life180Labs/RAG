"""Integration tests for the document_worker.finalize_upload task, run
against the real dockerized Postgres and MinIO (see conftest.py) rather
than mocks — the task's whole job is confirming that a real object landed
in real storage, so mocking storage would test nothing.
"""

import io
import uuid

from sqlalchemy import text

from common.db import SessionLocal
from common.storage import get_storage_client
from document_worker.tasks import finalize_upload


def _insert_document(repository_id, uploader_id, storage_key: str) -> uuid.UUID:
    document_id = uuid.uuid4()
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO documents (id, repository_id, filename, mime_type, size_bytes, "
                "sha256_hash, storage_key, status, current_version, uploaded_by) "
                "VALUES (:id, :repository_id, 'report.pdf', 'application/pdf', 12, "
                "'deadbeef', :storage_key, 'UPLOADED', 1, :uploaded_by)"
            ),
            {
                "id": document_id,
                "repository_id": repository_id,
                "storage_key": storage_key,
                "uploaded_by": uploader_id,
            },
        )
        session.commit()
    return document_id


def _document_status(document_id: uuid.UUID) -> tuple[str, str | None]:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT status, status_message FROM documents WHERE id = :id"),
            {"id": document_id},
        ).first()
        return row.status, row.status_message


def test_finalize_upload_marks_validated_when_object_exists(document_chain):
    storage_key = f"documents/{document_chain['repository_id']}/{uuid.uuid4()}/v1/report.pdf"
    client = get_storage_client()
    client.put_object(
        "rag-documents", storage_key, io.BytesIO(b"hello world"), length=len(b"hello world")
    )

    document_id = _insert_document(
        document_chain["repository_id"], document_chain["user_id"], storage_key
    )

    result = finalize_upload.run(str(document_id))

    assert result == {"status": "validated"}
    status, message = _document_status(document_id)
    assert status == "VALIDATED"
    assert message is None

    client.remove_object("rag-documents", storage_key)


def test_finalize_upload_marks_failed_validation_when_object_missing(document_chain):
    storage_key = f"documents/{document_chain['repository_id']}/{uuid.uuid4()}/v1/missing.pdf"
    document_id = _insert_document(
        document_chain["repository_id"], document_chain["user_id"], storage_key
    )

    result = finalize_upload.run(str(document_id))

    assert result == {"status": "failed_validation"}
    status, message = _document_status(document_id)
    assert status == "FAILED_VALIDATION"
    assert message == "Uploaded file could not be found in storage."


def test_finalize_upload_skips_when_document_not_found():
    result = finalize_upload.run(str(uuid.uuid4()))

    assert result == {"status": "skipped", "reason": "document_not_found"}
