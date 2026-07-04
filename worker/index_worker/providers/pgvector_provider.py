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
    UnsupportedIndexTypeError,
    VectorIndexProvider,
    VectorRecord,
)

_SUPPORTED_INDEX_TYPES = {"hnsw", "ivf_flat", "flat"}
_PG_ACCESS_METHOD = {"hnsw": "hnsw", "ivf_flat": "ivfflat"}


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
