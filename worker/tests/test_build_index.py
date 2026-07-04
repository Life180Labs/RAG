"""Integration tests for index_worker.build_index/delete_index, run
against the real dockerized Postgres + Qdrant (see conftest.py's
document_chain fixture) — mirrors the pattern in test_embed_chunk_set.py.
"""

import json
import uuid

from sqlalchemy import text

from chunk_worker.tasks import chunk_document
from common.db import SessionLocal
from embedding_worker.tasks import embed_chunk_set
from index_worker.tasks import build_index, delete_index

BLOCKS = [
    {"type": "heading", "text": "Section One", "level": 1, "page": None},
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


def _embedding_version_id(document_id: uuid.UUID) -> str:
    with SessionLocal() as session:
        chunk_set = session.execute(
            text("SELECT id FROM document_chunk_sets WHERE document_id = :id"),
            {"id": document_id},
        ).first()
        embed_chunk_set.run(str(chunk_set.id), "bge")
        version = session.execute(
            text(
                "SELECT id FROM embedding_versions WHERE chunk_set_id = :id AND provider = 'bge'"
            ),
            {"id": chunk_set.id},
        ).first()
        return str(version.id)


def _document_status(document_id: uuid.UUID) -> str:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT status FROM documents WHERE id = :id"), {"id": document_id}
        ).first()
        return row.status


def test_build_index_pgvector_end_to_end(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "structural")
    embedding_version_id = _embedding_version_id(document_id)

    result = build_index.run(embedding_version_id, "pgvector")

    assert result["status"] == "ready"
    assert result["vector_count"] > 0
    assert _document_status(document_id) == "READY"

    with SessionLocal() as session:
        index_row = session.execute(
            text(
                "SELECT id, status, vector_count, version FROM vector_indexes "
                "WHERE embedding_version_id = :id AND provider = 'pgvector'"
            ),
            {"id": embedding_version_id},
        ).first()
        assert index_row.status == "READY"
        assert index_row.version == 1

        metadata_rows = session.execute(
            text("SELECT metadata_payload FROM vector_metadata WHERE vector_index_id = :id"),
            {"id": index_row.id},
        ).all()
        assert len(metadata_rows) == index_row.vector_count
        assert any(m.metadata_payload.get("heading") == "Section One" for m in metadata_rows)


def test_build_index_regenerating_same_provider_bumps_version(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "structural")
    embedding_version_id = _embedding_version_id(document_id)

    build_index.run(embedding_version_id, "pgvector")
    build_index.run(embedding_version_id, "pgvector")

    with SessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT id, version FROM vector_indexes "
                "WHERE embedding_version_id = :id AND provider = 'pgvector'"
            ),
            {"id": embedding_version_id},
        ).all()
        assert len(rows) == 1
        assert rows[0].version == 2


def test_build_index_skips_when_embedding_version_not_found():
    result = build_index.run(str(uuid.uuid4()))
    assert result == {"status": "skipped", "reason": "embedding_version_not_found"}


def test_delete_index_removes_row_and_skips_when_missing(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "structural")
    embedding_version_id = _embedding_version_id(document_id)
    build_index.run(embedding_version_id, "pgvector")

    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT id FROM vector_indexes "
                "WHERE embedding_version_id = :id AND provider = 'pgvector'"
            ),
            {"id": embedding_version_id},
        ).first()
        vector_index_id = str(row.id)

    result = delete_index.run(vector_index_id)
    assert result["status"] == "deleted"

    with SessionLocal() as session:
        row = session.execute(
            text("SELECT id FROM vector_indexes WHERE id = :id"), {"id": vector_index_id}
        ).first()
        assert row is None

    skipped = delete_index.run(vector_index_id)
    assert skipped == {"status": "skipped", "reason": "vector_index_not_found"}
