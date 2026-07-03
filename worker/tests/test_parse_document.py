"""Integration tests for document_worker.parse_document, run against the
real dockerized Postgres + MinIO (see conftest.py's document_chain
fixture) — the task's job is downloading a real object and running the
real parser/cleaning/metadata pipeline, so mocking any of that would
test nothing.
"""

import io
import uuid

from sqlalchemy import text

from common.db import SessionLocal
from common.storage import get_storage_client
from document_worker.tasks import parse_document


def _insert_document(repository_id, uploader_id, storage_key: str, filename: str) -> uuid.UUID:
    document_id = uuid.uuid4()
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO documents (id, repository_id, filename, mime_type, size_bytes, "
                "sha256_hash, storage_key, status, current_version, uploaded_by) "
                "VALUES (:id, :repository_id, :filename, 'text/plain', 12, "
                "'deadbeef', :storage_key, 'VALIDATED', 1, :uploaded_by)"
            ),
            {
                "id": document_id,
                "repository_id": repository_id,
                "filename": filename,
                "storage_key": storage_key,
                "uploaded_by": uploader_id,
            },
        )
        session.commit()
    return document_id


def _document_status(document_id: uuid.UUID):
    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT status, status_message, language, page_count FROM documents "
                "WHERE id = :id"
            ),
            {"id": document_id},
        ).first()
        return row


def _document_content(document_id: uuid.UUID):
    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT raw_text, structured_content, language, word_count, parser_used, "
                "ocr_used FROM document_content WHERE document_id = :id"
            ),
            {"id": document_id},
        ).first()
        return row


def test_parse_document_txt_end_to_end(document_chain):
    storage_key = f"documents/{document_chain['repository_id']}/{uuid.uuid4()}/v1/report.txt"
    client = get_storage_client()
    content = b"My Report Title\n\nThe quick brown fox jumps over the lazy dog near the river."
    client.put_object("rag-documents", storage_key, io.BytesIO(content), length=len(content))

    document_id = _insert_document(
        document_chain["repository_id"], document_chain["user_id"], storage_key, "report.txt"
    )

    result = parse_document.run(str(document_id))

    assert result["status"] == "chunking"
    assert result["parser"] == "native"
    assert result["ocr_used"] is False

    document_row = _document_status(document_id)
    assert document_row.status == "CHUNKING"
    assert document_row.status_message is None
    assert document_row.language == "en"

    row = _document_content(document_id)
    assert row is not None
    assert "quick brown fox" in row.raw_text
    assert row.language == "en"
    assert row.word_count > 0
    assert row.parser_used == "native"
    assert row.ocr_used is False
    assert row.structured_content[0]["type"] == "title"

    client.remove_object("rag-documents", storage_key)


def test_parse_document_unsupported_extension_marks_failed_parse(document_chain):
    storage_key = f"documents/{document_chain['repository_id']}/{uuid.uuid4()}/v1/binary.exe"
    client = get_storage_client()
    content = b"not a real document"
    client.put_object("rag-documents", storage_key, io.BytesIO(content), length=len(content))

    document_id = _insert_document(
        document_chain["repository_id"], document_chain["user_id"], storage_key, "binary.exe"
    )

    result = parse_document.run(str(document_id))

    assert result["status"] == "failed_parse"
    document_row = _document_status(document_id)
    assert document_row.status == "FAILED_PARSE"
    assert document_row.status_message is not None

    client.remove_object("rag-documents", storage_key)


def test_parse_document_reparse_overwrites_existing_content_row(document_chain):
    storage_key = f"documents/{document_chain['repository_id']}/{uuid.uuid4()}/v1/note.txt"
    client = get_storage_client()
    content = b"First Version Title\n\nOriginal body text."
    client.put_object("rag-documents", storage_key, io.BytesIO(content), length=len(content))

    document_id = _insert_document(
        document_chain["repository_id"], document_chain["user_id"], storage_key, "note.txt"
    )

    parse_document.run(str(document_id))
    parse_document.run(str(document_id))

    with SessionLocal() as session:
        count = session.execute(
            text("SELECT COUNT(*) FROM document_content WHERE document_id = :id"),
            {"id": document_id},
        ).scalar_one()
    assert count == 1

    client.remove_object("rag-documents", storage_key)


def test_parse_document_skips_when_document_not_found():
    result = parse_document.run(str(uuid.uuid4()))

    assert result == {"status": "skipped", "reason": "document_not_found"}
