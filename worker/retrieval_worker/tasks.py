"""Dense retrieval execution (docs/05-task.md Phase 9;
docs/02-architecture.md section 56 Dense Retrieval).

`execute_retrieval` runs after the backend creates a `Retrieval` row
(status=PENDING): embeds the query text with the *same* provider/model
that produced the target vector index's embedding version — reusing
`common.embedding_providers` (promoted out of `embedding_worker` this
phase precisely so this package can use it without importing
`embedding_worker` directly) — then searches the index via
`index_worker.providers`' `search()` extension of Phase 8's provider
abstraction, and persists ranked `RetrievalResult` rows plus aggregate
stats (result_count, avg/min/max similarity, latency).

Raw SQL via a sync SQLAlchemy session, same as every other worker
package — this worker package is independently deployable and never
imports backend ORM models or another worker package's internals.
"""

import json
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from common.celery_app import celery_app
from common.db import SessionLocal
from common.embedding_providers.factory import get_provider as get_embedding_provider
from common.logging import get_logger
from index_worker.providers.base import UnsupportedMetricError
from index_worker.providers.factory import get_provider as get_index_provider

logger = get_logger(__name__)


def _fail(session, retrieval_id: str, message: str) -> None:
    session.execute(
        text(
            "UPDATE retrievals SET status = 'FAILED', status_message = :message, "
            "updated_at = :now WHERE id = :id"
        ),
        {"message": message[:500], "now": datetime.now(UTC), "id": retrieval_id},
    )
    session.commit()


@celery_app.task(
    name="retrieval_worker.execute_retrieval",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def execute_retrieval(retrieval_id: str) -> dict:
    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT r.query_text, r.top_k, r.score_threshold, r.similarity_metric, "
                "r.metadata_filter, vi.document_id, vi.provider AS index_provider, "
                "vi.namespace, ev.provider AS embed_provider, ev.model "
                "FROM retrievals r "
                "JOIN vector_indexes vi ON vi.id = r.vector_index_id "
                "JOIN embedding_versions ev ON ev.id = vi.embedding_version_id "
                "WHERE r.id = :id"
            ),
            {"id": retrieval_id},
        ).first()
        if row is None:
            logger.warning("execute_retrieval_missing", retrieval_id=retrieval_id)
            return {"status": "skipped", "reason": "retrieval_not_found"}

        metadata_filter = json.loads(row.metadata_filter) if row.metadata_filter else None
        metric = row.similarity_metric.lower()

        start = time.perf_counter()
        try:
            embedder = get_embedding_provider(row.embed_provider, row.model)
            query_vector = embedder.embed([row.query_text])[0].vector
        except Exception as exc:
            message = f"Query embedding failed: {exc}"[:500]
            _fail(session, retrieval_id, message)
            raise

        try:
            index_provider = get_index_provider(row.index_provider, session)
            hits = index_provider.search(
                row.namespace, query_vector, row.top_k, metric, row.score_threshold,
                metadata_filter,
            )
        except UnsupportedMetricError as exc:
            message = str(exc)
            _fail(session, retrieval_id, message)
            logger.warning(
                "execute_retrieval_unsupported_metric", retrieval_id=retrieval_id, error=message
            )
            return {"status": "failed", "reason": message}
        except Exception as exc:
            message = f"Search failed: {exc}"[:500]
            _fail(session, retrieval_id, message)
            raise
        latency_ms = int((time.perf_counter() - start) * 1000)

        session.execute(
            text("DELETE FROM retrieval_results WHERE retrieval_id = :id"), {"id": retrieval_id}
        )
        for rank, hit in enumerate(hits, start=1):
            session.execute(
                text(
                    "INSERT INTO retrieval_results (id, retrieval_id, chunk_id, rank, score) "
                    "VALUES (:id, :retrieval_id, :chunk_id, :rank, :score)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "retrieval_id": retrieval_id,
                    "chunk_id": hit.chunk_id,
                    "rank": rank,
                    "score": hit.score,
                },
            )

        scores = [hit.score for hit in hits]
        avg_similarity = sum(scores) / len(scores) if scores else None
        min_similarity = min(scores) if scores else None
        max_similarity = max(scores) if scores else None

        session.execute(
            text(
                "UPDATE retrievals SET status = 'COMPLETED', status_message = NULL, "
                "result_count = :count, avg_similarity = :avg, min_similarity = :min, "
                "max_similarity = :max, latency_ms = :latency, updated_at = :now "
                "WHERE id = :id"
            ),
            {
                "count": len(hits),
                "avg": avg_similarity,
                "min": min_similarity,
                "max": max_similarity,
                "latency": latency_ms,
                "now": datetime.now(UTC),
                "id": retrieval_id,
            },
        )

        session.execute(
            text(
                "UPDATE repositories SET retrieval_count = retrieval_count + 1, updated_at = :now "
                "WHERE id = (SELECT repository_id FROM documents WHERE id = :document_id)"
            ),
            {"now": datetime.now(UTC), "document_id": str(row.document_id)},
        )
        session.commit()

    logger.info(
        "execute_retrieval_completed",
        retrieval_id=retrieval_id,
        result_count=len(hits),
        latency_ms=latency_ms,
    )
    return {"status": "completed", "result_count": len(hits), "latency_ms": latency_ms}
