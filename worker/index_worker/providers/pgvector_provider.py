"""PgVector index provider (docs/05-task.md Phase 8).

Unlike the external stores, PgVector needs no data copy — vectors
already live in the `embeddings` table from Phase 7. "Building an index"
here means creating a real ANN index on that table, scoped to one
embedding_version via a partial index (`WHERE embedding_version_id =
...`). Populating `vector_metadata` is the calling task's job, uniformly
for every provider — not this provider's concern.

Index types actually supported: `hnsw` and `ivf_flat` are real pgvector
index access methods; `flat` is implemented as *no* ANN index at all
(pgvector's actual behavior without one — an exact sequential scan,
which is what "flat" legitimately means). `pq` (product quantization) is
not implemented — pgvector has no native PQ index type, a real
limitation rather than a deferral choice; requesting it raises
`UnsupportedIndexTypeError`.
"""

import re
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from index_worker.providers.base import (
    IndexStats,
    SearchHit,
    UnsupportedIndexTypeError,
    UnsupportedMetricError,
    VectorIndexProvider,
    VectorRecord,
)

_SUPPORTED_INDEX_TYPES = {"hnsw", "ivf_flat", "flat"}
_PG_ACCESS_METHOD = {"hnsw": "hnsw", "ivf_flat": "ivfflat"}

# Must match EMBEDDING_DIM_MAX in backend/app/models/embedding.py — a
# query vector must be zero-padded to the same fixed column width the
# stored embeddings use, or pgvector's distance operators reject the
# dimension mismatch.
_EMBEDDING_DIM_MAX = 1536

# pgvector distance operator per metric, and the score expression
# template that turns its raw output into a "higher is better" score
# (see base.VectorIndexProvider.search): cosine distance -> similarity,
# dot product's `<#>` is already negative so negating gives the true
# inner product, euclidean distance is negated so closer = higher score.
_METRIC_SCORE_EXPR: dict[str, str] = {
    "cosine": "1 - (e.embedding <=> '{query_literal}'::vector)",
    "dot": "-(e.embedding <#> '{query_literal}'::vector)",
    "euclidean": "-(e.embedding <-> '{query_literal}'::vector)",
}
# Only heading/page/language are ever attached as chunk metadata (Phase
# 8's index_worker.tasks), so pgvector's own metadata_filter can join
# straight to the chunks table these came from rather than needing its
# own copy of that data (unlike Qdrant/Chroma/Pinecone, which only have
# their own upserted copy to filter against).
_FILTERABLE_CHUNK_COLUMNS = {"heading", "page", "language"}


def _index_name(namespace: str) -> str:
    # Postgres identifiers must start with a letter/underscore and stay
    # under 63 bytes; namespace is a UUID string, so this is always safe.
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", namespace)
    return f"idx_embeddings_{safe}"


class PgVectorProvider(VectorIndexProvider):
    provider_name = "pgvector"

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_or_rebuild(
        self, namespace: str, index_type: str, dimensions: int, records: list[VectorRecord]
    ) -> IndexStats:
        if index_type not in _SUPPORTED_INDEX_TYPES:
            raise UnsupportedIndexTypeError(
                f"pgvector does not support index_type '{index_type}'."
            )

        # Validates namespace is really a UUID and normalizes it, so it's
        # safe to embed as a literal below — psycopg3's extended query
        # protocol can't infer a bound parameter's type inside a
        # `CREATE INDEX ... WHERE` predicate (a real driver limitation,
        # not a SQL injection shortcut: this value is never user input,
        # always the server-generated embedding_version_id).
        embedding_version_id = str(uuid.UUID(namespace))
        index_name = _index_name(namespace)

        self._session.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        if index_type in _PG_ACCESS_METHOD:
            method = _PG_ACCESS_METHOD[index_type]
            # ivfflat requires an explicit `lists` (no default); HNSW's
            # m/ef_construction defaults are fine for this scale, so only
            # ivfflat gets a WITH clause.
            with_clause = " WITH (lists = 100)" if method == "ivfflat" else ""
            self._session.execute(
                text(
                    f'CREATE INDEX "{index_name}" ON embeddings '
                    f"USING {method} (embedding vector_cosine_ops){with_clause} "
                    f"WHERE embedding_version_id = '{embedding_version_id}'::uuid"
                )
            )

        self._session.commit()

        return IndexStats(
            vector_count=len(records),
            dimensions=dimensions,
            extra={"index_name": index_name, "index_type": index_type},
        )

    def delete(self, namespace: str) -> None:
        index_name = _index_name(namespace)
        self._session.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        self._session.commit()

    def stats(self, namespace: str) -> IndexStats:
        embedding_version_id = namespace
        count_row = self._session.execute(
            text(
                "SELECT COUNT(*) AS count FROM embeddings "
                "WHERE embedding_version_id = :embedding_version_id AND status = 'READY'"
            ),
            {"embedding_version_id": embedding_version_id},
        ).first()
        dims_row = self._session.execute(
            text("SELECT dimensions FROM embedding_versions WHERE id = :id"),
            {"id": embedding_version_id},
        ).first()
        index_name = _index_name(namespace)
        index_exists = self._session.execute(
            text("SELECT 1 FROM pg_indexes WHERE indexname = :name"), {"name": index_name}
        ).first()
        return IndexStats(
            vector_count=count_row.count if count_row else 0,
            dimensions=dims_row.dimensions if dims_row else 0,
            extra={"index_name": index_name, "index_exists": bool(index_exists)},
        )

    def health_check(self) -> bool:
        self._session.execute(text("SELECT 1"))
        return True

    def search(
        self,
        namespace: str,
        query_vector: list[float],
        top_k: int,
        metric: str,
        score_threshold: float | None,
        metadata_filter: dict | None,
    ) -> list[SearchHit]:
        if metric not in _METRIC_SCORE_EXPR:
            raise UnsupportedMetricError(f"pgvector does not support metric '{metric}'.")

        embedding_version_id = str(uuid.UUID(namespace))
        padded = list(query_vector) + [0.0] * (_EMBEDDING_DIM_MAX - len(query_vector))
        # Same reasoning as create_or_rebuild's embedded namespace literal:
        # psycopg3 can't infer a bound parameter's vector type here either,
        # and this literal is built from floats we already validated by
        # padding to a fixed length, never raw user text.
        query_literal = "[" + ",".join(repr(float(x)) for x in padded) + "]"
        score_expr = _METRIC_SCORE_EXPR[metric].format(query_literal=query_literal)

        filter_clauses = []
        filter_params: dict = {}
        for key, value in (metadata_filter or {}).items():
            if key not in _FILTERABLE_CHUNK_COLUMNS:
                continue
            filter_clauses.append(f"c.{key} = :filter_{key}")
            filter_params[f"filter_{key}"] = value
        filter_sql = "".join(f" AND {clause}" for clause in filter_clauses)

        rows = self._session.execute(
            text(
                f"SELECT e.chunk_id, ({score_expr}) AS score, "
                "c.heading, c.page, c.language "
                "FROM embeddings e JOIN chunks c ON c.id = e.chunk_id "
                "WHERE e.embedding_version_id = :embedding_version_id AND e.status = 'READY'"
                f"{filter_sql} "
                "ORDER BY score DESC "
                "LIMIT :top_k"
            ),
            {
                "embedding_version_id": embedding_version_id,
                "top_k": top_k,
                **filter_params,
            },
        ).all()

        hits = [
            SearchHit(
                chunk_id=str(row.chunk_id),
                score=row.score,
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
        if score_threshold is not None:
            hits = [hit for hit in hits if hit.score >= score_threshold]
        return hits
