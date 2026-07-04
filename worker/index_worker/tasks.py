"""Vector index build tasks (docs/05-task.md Phase 8;
docs/02-architecture.md section 43).

`build_index` picks up where `embedding_worker.embed_chunk_set` leaves
off: it reads an embedding_version's READY embeddings (joined with their
chunks for metadata), pushes them into the selected vector provider, and
persists a `vector_indexes` row plus an `index_versions` audit entry
plus per-chunk `vector_metadata`. On success the document advances
INDEXING -> READY — the final state in the pipeline.

Re-running "create index" for the same (embedding_version, provider)
rebuilds it in place (same `vector_indexes` id, `version` bumped, a new
`index_versions` row appended) rather than accumulating duplicates — the
same regenerate-in-place pattern Phases 6-7 already established.

Raw SQL via a sync SQLAlchemy session, same as the other worker
packages — this worker package is independently deployable and never
imports backend ORM models or another worker package's internals.
"""

import json
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from common.celery_app import celery_app
from common.db import SessionLocal
from common.logging import get_logger
from index_worker.providers.base import (
    ProviderNotConfiguredError,
    UnsupportedIndexTypeError,
    VectorRecord,
)
from index_worker.providers.factory import DEFAULT_INDEX_TYPE, DEFAULT_PROVIDER, get_provider

logger = get_logger(__name__)


def _parse_vector_text(value: str) -> list[float]:
    # pgvector's text representation is "[0.1,0.2,...]"; the raw psycopg3
    # driver (no pgvector adapter registered on this sync engine) returns
    # it as a plain string, so it's parsed manually — the same manual
    # approach embedding_worker.tasks uses for the write side.
    return [float(x) for x in value.strip("[]").split(",")]


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


def _upsert_vector_index(session, **fields) -> None:
    session.execute(
        text(
            "INSERT INTO vector_indexes "
            "(id, embedding_version_id, document_id, provider, index_type, namespace, "
            "dimensions, version, status, status_message, vector_count, build_duration_ms, "
            "created_at, updated_at) "
            "VALUES (:id, :embedding_version_id, :document_id, :provider, :index_type, "
            ":namespace, :dimensions, :version, :status, :status_message, :vector_count, "
            ":build_duration_ms, :now, :now) "
            "ON CONFLICT (embedding_version_id, provider) DO UPDATE SET "
            "index_type = EXCLUDED.index_type, namespace = EXCLUDED.namespace, "
            "dimensions = EXCLUDED.dimensions, version = EXCLUDED.version, "
            "status = EXCLUDED.status, status_message = EXCLUDED.status_message, "
            "vector_count = EXCLUDED.vector_count, "
            "build_duration_ms = EXCLUDED.build_duration_ms, updated_at = EXCLUDED.updated_at"
        ),
        {**fields, "now": datetime.now(UTC)},
    )
    session.commit()


def _record_index_version(
    session,
    vector_index_id: str,
    version: int,
    vector_count: int,
    status: str,
    status_message: str | None,
    build_duration_ms: int | None,
) -> None:
    session.execute(
        text(
            "INSERT INTO index_versions "
            "(id, vector_index_id, version, vector_count, status, status_message, "
            "build_duration_ms) "
            "VALUES (:id, :vector_index_id, :version, :vector_count, :status, "
            ":status_message, :build_duration_ms)"
        ),
        {
            "id": str(uuid.uuid4()),
            "vector_index_id": vector_index_id,
            "version": version,
            "vector_count": vector_count,
            "status": status,
            "status_message": status_message,
            "build_duration_ms": build_duration_ms,
        },
    )
    session.commit()


@celery_app.task(
    name="index_worker.build_index",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def build_index(
    embedding_version_id: str, provider: str | None = None, index_type: str | None = None
) -> dict:
    with SessionLocal() as session:
        version_row = session.execute(
            text("SELECT document_id, dimensions FROM embedding_versions WHERE id = :id"),
            {"id": embedding_version_id},
        ).first()
        if version_row is None:
            logger.warning("build_index_missing", embedding_version_id=embedding_version_id)
            return {"status": "skipped", "reason": "embedding_version_not_found"}

        document_id = str(version_row.document_id)
        dimensions = version_row.dimensions

        rows = session.execute(
            text(
                "SELECT e.chunk_id, e.embedding::text AS embedding_text, "
                "c.heading, c.page, c.language "
                "FROM embeddings e JOIN chunks c ON c.id = e.chunk_id "
                "WHERE e.embedding_version_id = :id AND e.status = 'READY'"
            ),
            {"id": embedding_version_id},
        ).all()

        if not rows:
            message = "No ready embeddings found for this embedding version."
            _set_document_status(session, document_id, "FAILED_INDEX", message)
            logger.warning("build_index_no_embeddings", embedding_version_id=embedding_version_id)
            return {"status": "failed_index", "reason": message}

        resolved_provider = provider or DEFAULT_PROVIDER
        resolved_index_type = index_type or DEFAULT_INDEX_TYPE
        namespace = embedding_version_id

        old_index_row = session.execute(
            text(
                "SELECT id, version FROM vector_indexes "
                "WHERE embedding_version_id = :id AND provider = :provider"
            ),
            {"id": embedding_version_id, "provider": resolved_provider},
        ).first()
        vector_index_id = (
            str(old_index_row.id) if old_index_row is not None else str(uuid.uuid4())
        )
        next_version = (old_index_row.version + 1) if old_index_row is not None else 1

        def _fail(message: str) -> None:
            _upsert_vector_index(
                session,
                id=vector_index_id,
                embedding_version_id=embedding_version_id,
                document_id=document_id,
                provider=resolved_provider,
                index_type=resolved_index_type,
                namespace=namespace,
                dimensions=dimensions,
                version=next_version,
                status="FAILED",
                status_message=message,
                vector_count=0,
                build_duration_ms=None,
            )
            _record_index_version(
                session, vector_index_id, next_version, 0, "FAILED", message, None
            )
            _set_document_status(session, document_id, "FAILED_INDEX", message)

        records = [
            VectorRecord(
                chunk_id=str(row.chunk_id),
                vector=_parse_vector_text(row.embedding_text)[:dimensions],
                metadata={
                    k: v
                    for k, v in {
                        "heading": row.heading,
                        "page": row.page,
                        "language": row.language,
                    }.items()
                    if v is not None
                },
            )
            for row in rows
        ]

        try:
            provider_instance = get_provider(resolved_provider, session)
        except ProviderNotConfiguredError as exc:
            message = str(exc)
            _fail(message)
            logger.warning(
                "build_index_not_configured",
                embedding_version_id=embedding_version_id,
                provider=resolved_provider,
                error=message,
            )
            return {"status": "failed_index", "reason": message}

        start = time.perf_counter()
        try:
            stats = provider_instance.create_or_rebuild(
                namespace, resolved_index_type, dimensions, records
            )
        except UnsupportedIndexTypeError as exc:
            message = str(exc)
            _fail(message)
            logger.warning(
                "build_index_unsupported_type",
                embedding_version_id=embedding_version_id,
                provider=resolved_provider,
                index_type=resolved_index_type,
                error=message,
            )
            return {"status": "failed_index", "reason": message}
        except Exception as exc:
            message = f"Index build failed: {exc}"[:500]
            _fail(message)
            raise
        build_duration_ms = int((time.perf_counter() - start) * 1000)

        # vector_indexes must exist before vector_metadata rows can FK to
        # it — on a first build, vector_index_id hasn't been inserted yet.
        _upsert_vector_index(
            session,
            id=vector_index_id,
            embedding_version_id=embedding_version_id,
            document_id=document_id,
            provider=resolved_provider,
            index_type=resolved_index_type,
            namespace=namespace,
            dimensions=dimensions,
            version=next_version,
            status="READY",
            status_message=None,
            vector_count=stats.vector_count,
            build_duration_ms=build_duration_ms,
        )

        session.execute(
            text("DELETE FROM vector_metadata WHERE vector_index_id = :id"),
            {"id": vector_index_id},
        )
        for record in records:
            session.execute(
                text(
                    "INSERT INTO vector_metadata "
                    "(id, vector_index_id, chunk_id, metadata_payload) "
                    "VALUES (:id, :vector_index_id, :chunk_id, CAST(:metadata AS jsonb))"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "vector_index_id": vector_index_id,
                    "chunk_id": record.chunk_id,
                    "metadata": json.dumps(record.metadata),
                },
            )
        session.commit()

        _record_index_version(
            session,
            vector_index_id,
            next_version,
            stats.vector_count,
            "READY",
            None,
            build_duration_ms,
        )

        _set_document_status(session, document_id, "READY")

    logger.info(
        "build_index_completed",
        embedding_version_id=embedding_version_id,
        provider=resolved_provider,
        vector_count=stats.vector_count,
    )
    return {
        "status": "ready",
        "provider": resolved_provider,
        "index_type": resolved_index_type,
        "vector_count": stats.vector_count,
    }


@celery_app.task(
    name="index_worker.delete_index",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def delete_index(vector_index_id: str) -> dict:
    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT provider, namespace FROM vector_indexes WHERE id = :id"
            ),
            {"id": vector_index_id},
        ).first()
        if row is None:
            logger.warning("delete_index_missing", vector_index_id=vector_index_id)
            return {"status": "skipped", "reason": "vector_index_not_found"}

        provider_instance = get_provider(row.provider, session)
        provider_instance.delete(row.namespace)

        session.execute(
            text("DELETE FROM vector_indexes WHERE id = :id"), {"id": vector_index_id}
        )
        session.commit()

    logger.info("delete_index_completed", vector_index_id=vector_index_id, provider=row.provider)
    return {"status": "deleted", "provider": row.provider}
