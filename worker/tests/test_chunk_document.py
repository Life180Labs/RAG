"""Integration tests for chunk_worker.chunk_document, run against the
real dockerized Postgres (see conftest.py's document_chain fixture) —
mirrors the pattern in test_parse_document.py.
"""

import json
import uuid

from sqlalchemy import text

from chunk_worker.tasks import chunk_document
from common.db import SessionLocal

BLOCKS = [
    {"type": "title", "text": "Test Doc", "level": None, "page": None},
    {
        "type": "paragraph",
        "text": "Sentence one here. Sentence two here. Sentence three here. Sentence four here.",
        "level": None,
        "page": None,
    },
]


def _insert_document_with_content(repository_id, uploader_id) -> uuid.UUID:
    document_id = uuid.uuid4()
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO documents (id, repository_id, filename, mime_type, size_bytes, "
                "sha256_hash, storage_key, status, current_version, uploaded_by) "
                "VALUES (:id, :repository_id, 'a.txt', 'text/plain', 10, 'x', 'k', "
                "'CHUNKING', 1, :uploaded_by)"
            ),
            {"id": document_id, "repository_id": repository_id, "uploaded_by": uploader_id},
        )
        session.execute(
            text(
                "INSERT INTO document_content (id, document_id, version, raw_text, "
                "structured_content, parser_used, ocr_used, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :document_id, 1, 'raw', CAST(:blocks AS jsonb), "
                "'native', false, now(), now())"
            ),
            {"document_id": document_id, "blocks": json.dumps(BLOCKS)},
        )
        session.commit()
    return document_id


def _document_status(document_id: uuid.UUID) -> str:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT status FROM documents WHERE id = :id"), {"id": document_id}
        ).first()
        return row.status


def _repository_chunk_count(repository_id) -> int:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT chunk_count FROM repositories WHERE id = :id"), {"id": repository_id}
        ).first()
        return row.chunk_count


def test_chunk_document_end_to_end(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )

    result = chunk_document.run(str(document_id), "sentence")

    assert result["status"] == "embedding"
    assert result["strategy"] == "sentence"
    assert result["chunk_count"] > 0
    assert _document_status(document_id) == "EMBEDDING"
    assert _repository_chunk_count(document_chain["repository_id"]) == result["chunk_count"]

    with SessionLocal() as session:
        chunk_set = session.execute(
            text(
                "SELECT id, status, chunk_count FROM document_chunk_sets "
                "WHERE document_id = :id AND strategy = 'sentence'"
            ),
            {"id": document_id},
        ).first()
        assert chunk_set.status == "READY"

        chunks = session.execute(
            text("SELECT chunk_index, text, status FROM chunks WHERE chunk_set_id = :id"),
            {"id": chunk_set.id},
        ).all()
        assert len(chunks) == chunk_set.chunk_count
        assert all(c.status == "READY" for c in chunks)


def test_chunk_document_regenerating_same_strategy_replaces_set(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )

    chunk_document.run(str(document_id), "sentence")
    chunk_document.run(str(document_id), "sentence")

    with SessionLocal() as session:
        sets = session.execute(
            text(
                "SELECT id FROM document_chunk_sets "
                "WHERE document_id = :id AND strategy = 'sentence'"
            ),
            {"id": document_id},
        ).all()
        assert len(sets) == 1


def test_chunk_document_different_strategies_coexist_for_comparison(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )

    chunk_document.run(str(document_id), "sentence")
    chunk_document.run(str(document_id), "paragraph")

    with SessionLocal() as session:
        sets = session.execute(
            text(
                "SELECT strategy FROM document_chunk_sets WHERE document_id = :id ORDER BY strategy"
            ),
            {"id": document_id},
        ).all()
        assert [s.strategy for s in sets] == ["paragraph", "sentence"]


def test_chunk_document_skips_when_document_not_found():
    result = chunk_document.run(str(uuid.uuid4()), "recursive")
    assert result == {"status": "skipped", "reason": "document_not_found"}


def test_chunk_document_fails_when_no_parsed_content(document_chain):
    document_id = uuid.uuid4()
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO documents (id, repository_id, filename, mime_type, size_bytes, "
                "sha256_hash, storage_key, status, current_version, uploaded_by) "
                "VALUES (:id, :repository_id, 'a.txt', 'text/plain', 10, 'x', 'k', "
                "'CHUNKING', 1, :uploaded_by)"
            ),
            {
                "id": document_id,
                "repository_id": document_chain["repository_id"],
                "uploaded_by": document_chain["user_id"],
            },
        )
        session.commit()

    result = chunk_document.run(str(document_id), "recursive")

    assert result["status"] == "failed_chunk"
    assert _document_status(document_id) == "FAILED_CHUNK"
