"""Embedding generation tasks (docs/05-task.md Phase 7;
docs/02-architecture.md section 40).

`embed_chunk_set` picks up where `chunk_worker.chunk_document` leaves
off: it reads a chunk set's READY chunks, runs the selected provider in
batches, and persists an `embedding_versions` row plus its `embeddings`.
On success the document advances EMBEDDING -> INDEXING — the
"ready for the next phase" marker, same pattern as CHUNKING meaning
"ready for chunking" at the end of Phase 5.

Re-running the *same* (chunk_set, provider, model) combination replaces
its embedding version in place (reusing the id, bumping `version`)
rather than accumulating duplicates — the same regeneration-reuses-id
fix Phase 6 needed for chunk sets, applied here from the start.

Raw SQL via a sync SQLAlchemy session, same as chunk_worker/document_worker
— this worker package is independently deployable and never imports
backend ORM models or another worker package's internals.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from common.celery_app import celery_app
from common.credentials import get_org_credential
from common.db import SessionLocal
from common.embedding_providers.base import ProviderNotConfiguredError
from common.embedding_providers.factory import DEFAULT_PROVIDER, default_model, get_provider
from common.logging import get_logger
from common.org_resolution import resolve_organization_id

logger = get_logger(__name__)

# Must match EMBEDDING_DIM_MAX in backend/app/models/embedding.py — the
# fixed pgvector column width every provider's vector is zero-padded to.
EMBEDDING_DIM_MAX = 1536
BATCH_SIZE = 64


def _vector_literal(vector: list[float]) -> str:
    padded = list(vector) + [0.0] * (EMBEDDING_DIM_MAX - len(vector))
    return "[" + ",".join(repr(float(x)) for x in padded) + "]"


def _set_document_status(
    session, document_id: str, status: str, message: str | None = None
) -> None:
    session.execute(
        text(
            "UPDATE documents SET status = :status, status_message = :message, "
            "updated_at = :now WHERE id = :id"
        ),
        {"status": status, "message": message, "now": datetime.now(UTC), "id": document_id},
    )
    session.commit()


def _upsert_embedding_version(session, **fields) -> None:
    session.execute(
        text(
            "INSERT INTO embedding_versions "
            "(id, chunk_set_id, document_id, provider, model, dimensions, version, status, "
            "status_message, embedding_count, total_tokens, total_cost_usd, avg_latency_ms, "
            "created_at, updated_at) "
            "VALUES (:id, :chunk_set_id, :document_id, :provider, :model, :dimensions, :version, "
            ":status, :status_message, :embedding_count, :total_tokens, :total_cost_usd, "
            ":avg_latency_ms, :now, :now) "
            "ON CONFLICT (chunk_set_id, provider, model) DO UPDATE SET "
            "dimensions = EXCLUDED.dimensions, version = EXCLUDED.version, "
            "status = EXCLUDED.status, status_message = EXCLUDED.status_message, "
            "embedding_count = EXCLUDED.embedding_count, total_tokens = EXCLUDED.total_tokens, "
            "total_cost_usd = EXCLUDED.total_cost_usd, avg_latency_ms = EXCLUDED.avg_latency_ms, "
            "updated_at = EXCLUDED.updated_at"
        ),
        {**fields, "now": datetime.now(UTC)},
    )
    session.commit()


@celery_app.task(
    name="embedding_worker.embed_chunk_set",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def embed_chunk_set(
    chunk_set_id: str, provider: str | None = None, model: str | None = None
) -> dict:
    with SessionLocal() as session:
        chunk_set_row = session.execute(
            text("SELECT document_id FROM document_chunk_sets WHERE id = :id"),
            {"id": chunk_set_id},
        ).first()
        if chunk_set_row is None:
            logger.warning("embed_chunk_set_missing", chunk_set_id=chunk_set_id)
            return {"status": "skipped", "reason": "chunk_set_not_found"}

        document_id = str(chunk_set_row.document_id)

        chunk_rows = session.execute(
            text(
                "SELECT id, text FROM chunks "
                "WHERE chunk_set_id = :chunk_set_id AND status = 'READY' ORDER BY chunk_index"
            ),
            {"chunk_set_id": chunk_set_id},
        ).all()

        if not chunk_rows:
            message = "No ready chunks found for this chunk set."
            _set_document_status(session, document_id, "FAILED_EMBED", message)
            logger.warning("embed_chunk_set_no_chunks", chunk_set_id=chunk_set_id)
            return {"status": "failed_embed", "reason": message}

        resolved_provider = provider or DEFAULT_PROVIDER
        resolved_model = model or default_model(resolved_provider)

        old_version_row = session.execute(
            text(
                "SELECT id, version, embedding_count FROM embedding_versions "
                "WHERE chunk_set_id = :chunk_set_id AND provider = :provider AND model = :model"
            ),
            {
                "chunk_set_id": chunk_set_id,
                "provider": resolved_provider,
                "model": resolved_model,
            },
        ).first()
        embedding_version_id = (
            str(old_version_row.id) if old_version_row is not None else str(uuid.uuid4())
        )
        next_version = (old_version_row.version + 1) if old_version_row is not None else 1
        old_embedding_count = old_version_row.embedding_count if old_version_row is not None else 0

        organization_id = resolve_organization_id(session, document_id)
        api_key_override = (
            get_org_credential(session, organization_id, resolved_provider)
            if organization_id
            else None
        )

        try:
            embedder = get_provider(resolved_provider, resolved_model, api_key_override)
        except ProviderNotConfiguredError as exc:
            message = str(exc)
            _upsert_embedding_version(
                session,
                id=embedding_version_id,
                chunk_set_id=chunk_set_id,
                document_id=document_id,
                provider=resolved_provider,
                model=resolved_model,
                dimensions=0,
                version=next_version,
                status="FAILED",
                status_message=message,
                embedding_count=0,
                total_tokens=0,
                total_cost_usd=None,
                avg_latency_ms=None,
            )
            _set_document_status(session, document_id, "FAILED_EMBED", message)
            logger.warning(
                "embed_chunk_set_not_configured",
                chunk_set_id=chunk_set_id,
                provider=resolved_provider,
                error=message,
            )
            return {"status": "failed_embed", "reason": message}

        if old_version_row is not None:
            session.execute(
                text("DELETE FROM embeddings WHERE embedding_version_id = :id"),
                {"id": embedding_version_id},
            )

        texts = [row.text for row in chunk_rows]
        chunk_ids = [str(row.id) for row in chunk_rows]

        try:
            results = []
            for start in range(0, len(texts), BATCH_SIZE):
                results.extend(embedder.embed(texts[start : start + BATCH_SIZE]))
        except Exception as exc:
            message = f"Embedding generation failed: {exc}"[:500]
            _upsert_embedding_version(
                session,
                id=embedding_version_id,
                chunk_set_id=chunk_set_id,
                document_id=document_id,
                provider=resolved_provider,
                model=resolved_model,
                dimensions=0,
                version=next_version,
                status="FAILED",
                status_message=message,
                embedding_count=0,
                total_tokens=0,
                total_cost_usd=None,
                avg_latency_ms=None,
            )
            _set_document_status(session, document_id, "FAILED_EMBED", message)
            raise

        total_tokens = sum(r.token_count for r in results)
        costs = [r.cost_usd for r in results if r.cost_usd is not None]
        total_cost = sum(costs) if costs else None
        avg_latency = int(sum(r.latency_ms for r in results) / len(results)) if results else 0
        dimensions = results[0].dimensions if results else 0

        _upsert_embedding_version(
            session,
            id=embedding_version_id,
            chunk_set_id=chunk_set_id,
            document_id=document_id,
            provider=resolved_provider,
            model=resolved_model,
            dimensions=dimensions,
            version=next_version,
            status="READY",
            status_message=None,
            embedding_count=len(results),
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            avg_latency_ms=avg_latency,
        )

        for chunk_id, result in zip(chunk_ids, results, strict=True):
            session.execute(
                text(
                    "INSERT INTO embeddings "
                    "(id, embedding_version_id, chunk_id, embedding, token_count, cost_usd, "
                    "latency_ms, status, status_message) "
                    "VALUES (:id, :embedding_version_id, :chunk_id, CAST(:embedding AS vector), "
                    ":token_count, :cost_usd, :latency_ms, 'READY', NULL)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "embedding_version_id": embedding_version_id,
                    "chunk_id": chunk_id,
                    "embedding": _vector_literal(result.vector),
                    "token_count": result.token_count,
                    "cost_usd": result.cost_usd,
                    "latency_ms": result.latency_ms,
                },
            )
        session.commit()

        session.execute(
            text(
                "UPDATE repositories SET embedding_count = GREATEST(0, embedding_count "
                "- :old + :new), updated_at = :now "
                "WHERE id = (SELECT repository_id FROM documents WHERE id = :document_id)"
            ),
            {
                "old": old_embedding_count,
                "new": len(results),
                "now": datetime.now(UTC),
                "document_id": document_id,
            },
        )
        session.commit()

        _set_document_status(session, document_id, "INDEXING")

    # By task name, not a Python import of index_worker — same
    # deployable-independence reasoning as chunk_worker's embedding_worker
    # handoff.
    celery_app.send_task("index_worker.build_index", args=[embedding_version_id])

    logger.info(
        "embed_chunk_set_completed",
        chunk_set_id=chunk_set_id,
        provider=resolved_provider,
        model=resolved_model,
        embedding_count=len(results),
    )
    return {
        "status": "indexing",
        "provider": resolved_provider,
        "model": resolved_model,
        "embedding_count": len(results),
    }
