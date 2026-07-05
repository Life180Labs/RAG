"""Retrieval Cache tests (docs/05-task.md Phase 17; docs/02-architecture.md
section 100). Run against the real dockerized Postgres + Redis — reuses
`test_execute_retrieval.py`'s document/index-building helpers rather than
duplicating them.
"""

import uuid

from sqlalchemy import text

from common import cache
from common.db import SessionLocal
from index_worker.tasks import build_index
from retrieval_worker.tasks import execute_retrieval
from tests.test_execute_retrieval import (
    _build_pgvector_index,
    _insert_document_with_content,
    _insert_retrieval,
)


def _metric_counts() -> tuple[int, int]:
    client = cache._client()  # noqa: SLF001 - test reaches into the module directly
    hits = int(client.get(f"{cache.METRICS_KEY_PREFIX}:retrieval:hits") or 0)
    misses = int(client.get(f"{cache.METRICS_KEY_PREFIX}:retrieval:misses") or 0)
    return hits, misses


def test_execute_retrieval_second_identical_call_is_a_cache_hit(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)

    retrieval_id_1 = _insert_retrieval(vector_index_id, document_id)
    hits_before, misses_before = _metric_counts()
    result_1 = execute_retrieval.run(retrieval_id_1)
    hits_after_1, misses_after_1 = _metric_counts()

    assert result_1["status"] == "completed"
    # First call for this exact key must be a miss (nothing cached yet).
    assert misses_after_1 == misses_before + 1
    assert hits_after_1 == hits_before

    retrieval_id_2 = _insert_retrieval(vector_index_id, document_id)
    result_2 = execute_retrieval.run(retrieval_id_2)
    hits_after_2, misses_after_2 = _metric_counts()

    assert result_2["status"] == "completed"
    # Identical query/params against the same (unchanged) index -> hit.
    assert hits_after_2 == hits_after_1 + 1
    assert misses_after_2 == misses_after_1

    with SessionLocal() as session:
        rows_1 = session.execute(
            text(
                "SELECT chunk_id, rank, score FROM retrieval_results "
                "WHERE retrieval_id = :id ORDER BY rank"
            ),
            {"id": retrieval_id_1},
        ).all()
        rows_2 = session.execute(
            text(
                "SELECT chunk_id, rank, score FROM retrieval_results "
                "WHERE retrieval_id = :id ORDER BY rank"
            ),
            {"id": retrieval_id_2},
        ).all()
        assert [(r.chunk_id, r.rank, r.score) for r in rows_1] == [
            (r.chunk_id, r.rank, r.score) for r in rows_2
        ]

        retrieval_2_row = session.execute(
            text("SELECT status, result_count FROM retrievals WHERE id = :id"),
            {"id": retrieval_id_2},
        ).first()
        assert retrieval_2_row.status == "COMPLETED"
        assert retrieval_2_row.result_count == result_1["result_count"]


def test_execute_retrieval_cache_invalidated_after_index_rebuild(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)

    retrieval_id_1 = _insert_retrieval(vector_index_id, document_id)
    execute_retrieval.run(retrieval_id_1)

    with SessionLocal() as session:
        embedding_version_id = session.execute(
            text("SELECT embedding_version_id FROM vector_indexes WHERE id = :id"),
            {"id": vector_index_id},
        ).first().embedding_version_id

    # Rebuild the same index (same id, version bumped) — this must
    # invalidate the previous cache entry rather than serving stale
    # results forever.
    build_index.run(str(embedding_version_id), "pgvector")

    retrieval_id_2 = _insert_retrieval(vector_index_id, document_id)
    misses_before = _metric_counts()[1]
    result_2 = execute_retrieval.run(retrieval_id_2)
    misses_after = _metric_counts()[1]

    assert result_2["status"] == "completed"
    assert misses_after == misses_before + 1


def test_execute_retrieval_different_query_is_a_cache_miss(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)

    retrieval_id_1 = _insert_retrieval(
        vector_index_id, document_id, query_text=f"query-{uuid.uuid4()}"
    )
    execute_retrieval.run(retrieval_id_1)

    retrieval_id_2 = _insert_retrieval(
        vector_index_id, document_id, query_text=f"query-{uuid.uuid4()}"
    )
    misses_before = _metric_counts()[1]
    result_2 = execute_retrieval.run(retrieval_id_2)
    misses_after = _metric_counts()[1]

    assert result_2["status"] == "completed"
    assert misses_after == misses_before + 1
