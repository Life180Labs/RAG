"""Semantic cache lookup/upsert (docs/02-architecture.md section 99:
embed the incoming query, vector-search past cached queries, and return
the cached answer directly when similarity clears a threshold instead of
re-running the full RAG pipeline).

Pure pgvector similarity over `SemanticCacheEntry` — no Redis involved,
since finding the *nearest* past query is an ANN/similarity search only
Postgres's pgvector extension can do here; this deployment's Redis
(plain `redis:7-alpine`) has no vector search module.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import metrics
from app.core.config import get_settings
from app.models.cache import SemanticCacheEntry
from app.models.embedding import EMBEDDING_DIM_MAX


def pad_embedding(vector: list[float]) -> list[float]:
    """Zero-pad a raw provider vector to the fixed pgvector column width,
    the same convention `app/models/embedding.py` and
    `worker/embedding_worker/tasks.py` already use for `embeddings.embedding`.
    """
    if len(vector) > EMBEDDING_DIM_MAX:
        raise ValueError(f"embedding dimension {len(vector)} exceeds EMBEDDING_DIM_MAX")
    return list(vector) + [0.0] * (EMBEDDING_DIM_MAX - len(vector))


async def find_similar(
    session: AsyncSession, vector_index_id: uuid.UUID, query_vector: list[float]
) -> SemanticCacheEntry | None:
    """Return the nearest cached entry for this vector index if its cosine
    similarity to `query_vector` clears `settings.semantic_cache_similarity_threshold`,
    else None. Scoped to `vector_index_id` — a cached answer from a
    different index's documents must never leak into this one's results.
    """
    settings = get_settings()
    padded = pad_embedding(query_vector)
    distance = SemanticCacheEntry.query_embedding.cosine_distance(padded)

    stmt = (
        select(SemanticCacheEntry, distance.label("distance"))
        .where(SemanticCacheEntry.vector_index_id == vector_index_id)
        .order_by(distance)
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        await metrics.record_miss("semantic")
        return None

    entry, cosine_distance = row
    similarity = 1 - cosine_distance
    if similarity < settings.semantic_cache_similarity_threshold:
        await metrics.record_miss("semantic")
        return None
    await metrics.record_hit("semantic")
    return entry


async def upsert_entry(
    session: AsyncSession,
    *,
    repository_id: uuid.UUID,
    vector_index_id: uuid.UUID,
    query_text: str,
    query_vector: list[float],
    answer_text: str,
) -> SemanticCacheEntry:
    entry = SemanticCacheEntry(
        repository_id=repository_id,
        vector_index_id=vector_index_id,
        query_text=query_text,
        query_embedding=pad_embedding(query_vector),
        answer_text=answer_text,
    )
    session.add(entry)
    await session.flush()
    return entry
