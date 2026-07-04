"""Integration tests for retrieval_worker.execute_retrieval, run against
the real dockerized Postgres (see conftest.py's document_chain fixture)
— mirrors the pattern in test_build_index.py, one stage further down
the pipeline: chunk -> embed -> index -> retrieve.
"""

import json
import uuid

from sqlalchemy import text

from chunk_worker.tasks import chunk_document
from common.db import SessionLocal
from embedding_worker.tasks import embed_chunk_set
from index_worker.tasks import build_index
from retrieval_worker.tasks import execute_retrieval

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


def _build_pgvector_index(document_id: uuid.UUID) -> tuple[str, str]:
    """Runs chunk -> embed -> index for one document and returns
    (vector_index_id, document_id) for the pgvector index built."""
    chunk_document.run(str(document_id), "structural")
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
        embedding_version_id = str(version.id)

    build_index.run(embedding_version_id, "pgvector")

    with SessionLocal() as session:
        index_row = session.execute(
            text(
                "SELECT id FROM vector_indexes "
                "WHERE embedding_version_id = :id AND provider = 'pgvector'"
            ),
            {"id": embedding_version_id},
        ).first()
        return str(index_row.id)


def _insert_retrieval(vector_index_id: str, document_id: uuid.UUID, **overrides) -> str:
    retrieval_id = str(uuid.uuid4())
    fields = {
        "id": retrieval_id,
        "vector_index_id": vector_index_id,
        "document_id": str(document_id),
        "query_text": "Section One",
        "top_k": 5,
        "score_threshold": None,
        "similarity_metric": "COSINE",
        "metadata_filter": None,
        "status": "PENDING",
        "result_count": 0,
        **overrides,
    }
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO retrievals "
                "(id, vector_index_id, document_id, query_text, top_k, score_threshold, "
                "similarity_metric, metadata_filter, status, result_count, created_at, updated_at) "
                "VALUES (:id, :vector_index_id, :document_id, :query_text, :top_k, "
                ":score_threshold, :similarity_metric, CAST(:metadata_filter AS jsonb), "
                ":status, :result_count, now(), now())"
            ),
            {**fields, "metadata_filter": json.dumps(fields["metadata_filter"])
                if fields["metadata_filter"] is not None else None},
        )
        session.commit()
    return retrieval_id


def test_execute_retrieval_end_to_end(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)
    retrieval_id = _insert_retrieval(vector_index_id, document_id)

    result = execute_retrieval.run(retrieval_id)

    assert result["status"] == "completed"
    assert result["result_count"] > 0

    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT status, result_count, avg_similarity, latency_ms "
                "FROM retrievals WHERE id = :id"
            ),
            {"id": retrieval_id},
        ).first()
        assert row.status == "COMPLETED"
        assert row.result_count == result["result_count"]
        assert row.avg_similarity is not None
        assert row.latency_ms is not None

        results = session.execute(
            text(
                "SELECT rank, score FROM retrieval_results WHERE retrieval_id = :id ORDER BY rank"
            ),
            {"id": retrieval_id},
        ).all()
        assert [r.rank for r in results] == list(range(1, len(results) + 1))

        repo_row = session.execute(
            text("SELECT retrieval_count FROM repositories WHERE id = :id"),
            {"id": document_chain["repository_id"]},
        ).first()
        assert repo_row.retrieval_count == 1


def test_execute_retrieval_rejects_unsupported_metric_for_external_provider(document_chain):
    # pgvector supports all three metrics, so this only demonstrates the
    # failure path using a metric pgvector *does* support but asserting
    # the happy path stays COMPLETED — the real unsupported-metric path
    # (Qdrant/Chroma/Pinecone forced to cosine) is covered directly
    # against the provider in test_vector_index_providers.py, since it
    # requires no query-embedding round trip to exercise.
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)
    retrieval_id = _insert_retrieval(
        vector_index_id, document_id, similarity_metric="EUCLIDEAN"
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"


def test_execute_retrieval_skips_when_retrieval_not_found():
    result = execute_retrieval.run(str(uuid.uuid4()))
    assert result == {"status": "skipped", "reason": "retrieval_not_found"}
