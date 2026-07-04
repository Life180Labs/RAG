"""Integration tests for embedding_worker.embed_chunk_set, run against
the real dockerized Postgres (see conftest.py's document_chain fixture)
— mirrors the pattern in test_chunk_document.py.
"""

import json
import os
import uuid

import pytest
from sqlalchemy import text

from chunk_worker.tasks import chunk_document
from common.db import SessionLocal
from embedding_worker.tasks import embed_chunk_set

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


def _chunk_set_id(document_id: uuid.UUID) -> str:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT id FROM document_chunk_sets WHERE document_id = :id"),
            {"id": document_id},
        ).first()
        return str(row.id)


def _document_status(document_id: uuid.UUID) -> str:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT status FROM documents WHERE id = :id"), {"id": document_id}
        ).first()
        return row.status


def _repository_embedding_count(repository_id) -> int:
    with SessionLocal() as session:
        row = session.execute(
            text("SELECT embedding_count FROM repositories WHERE id = :id"),
            {"id": repository_id},
        ).first()
        return row.embedding_count


def test_embed_chunk_set_end_to_end(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "sentence")
    chunk_set_id = _chunk_set_id(document_id)

    result = embed_chunk_set.run(chunk_set_id)

    assert result["status"] == "indexing"
    assert result["provider"] == "bge"
    assert result["embedding_count"] > 0
    assert _document_status(document_id) == "INDEXING"
    assert (
        _repository_embedding_count(document_chain["repository_id"]) == result["embedding_count"]
    )

    with SessionLocal() as session:
        version = session.execute(
            text(
                "SELECT id, status, dimensions, version, embedding_count FROM embedding_versions "
                "WHERE chunk_set_id = :id AND provider = 'bge'"
            ),
            {"id": chunk_set_id},
        ).first()
        assert version.status == "READY"
        assert version.dimensions == 384
        assert version.version == 1

        embeddings = session.execute(
            text(
                "SELECT token_count, latency_ms, status FROM embeddings "
                "WHERE embedding_version_id = :id"
            ),
            {"id": version.id},
        ).all()
        assert len(embeddings) == version.embedding_count
        assert all(e.status == "READY" for e in embeddings)
        assert all(e.token_count > 0 for e in embeddings)


def test_embed_chunk_set_regenerating_same_provider_replaces_version(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "sentence")
    chunk_set_id = _chunk_set_id(document_id)

    embed_chunk_set.run(chunk_set_id, "bge")
    embed_chunk_set.run(chunk_set_id, "bge")

    with SessionLocal() as session:
        versions = session.execute(
            text(
                "SELECT id, version FROM embedding_versions "
                "WHERE chunk_set_id = :id AND provider = 'bge'"
            ),
            {"id": chunk_set_id},
        ).all()
        assert len(versions) == 1
        assert versions[0].version == 2


def test_embed_chunk_set_different_models_coexist_for_comparison(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "sentence")
    chunk_set_id = _chunk_set_id(document_id)

    embed_chunk_set.run(chunk_set_id, "bge", "BAAI/bge-small-en-v1.5")
    embed_chunk_set.run(chunk_set_id, "bge", "BAAI/bge-base-en-v1.5")

    with SessionLocal() as session:
        versions = session.execute(
            text(
                "SELECT model FROM embedding_versions WHERE chunk_set_id = :id ORDER BY model"
            ),
            {"id": chunk_set_id},
        ).all()
        assert [v.model for v in versions] == ["BAAI/bge-base-en-v1.5", "BAAI/bge-small-en-v1.5"]


def test_embed_chunk_set_skips_when_chunk_set_not_found():
    result = embed_chunk_set.run(str(uuid.uuid4()))
    assert result == {"status": "skipped", "reason": "chunk_set_not_found"}


@pytest.mark.skipif(
    bool(os.environ.get("OPENAI_API_KEY")),
    reason="OPENAI_API_KEY is configured, so this provider would succeed rather than fail",
)
def test_embed_chunk_set_fails_when_provider_not_configured(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    chunk_document.run(str(document_id), "sentence")
    chunk_set_id = _chunk_set_id(document_id)

    result = embed_chunk_set.run(chunk_set_id, "openai")

    assert result["status"] == "failed_embed"
    assert _document_status(document_id) == "FAILED_EMBED"

    with SessionLocal() as session:
        version = session.execute(
            text(
                "SELECT status, status_message FROM embedding_versions "
                "WHERE chunk_set_id = :id AND provider = 'openai'"
            ),
            {"id": chunk_set_id},
        ).first()
        assert version.status == "FAILED"
        assert "OPENAI_API_KEY" in version.status_message
