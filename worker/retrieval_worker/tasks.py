"""Dense + hybrid retrieval execution (docs/05-task.md Phases 9-12;
docs/02-architecture.md sections 56 Dense Retrieval, 57 Sparse
Retrieval, 58 Hybrid Search, 62-63 MMR/Parent-Child, 75 Context
Compression, 103 RAG Fusion).

`execute_retrieval` runs after the backend creates a `Retrieval` row
(status=PENDING): embeds the query text with the *same* provider/model
that produced the target vector index's embedding version — reusing
`common.embedding_providers` (promoted out of `embedding_worker` in
Phase 9 precisely so this package can use it without importing
`embedding_worker` directly) — then searches the index via
`index_worker.providers`' `search()` extension of Phase 8's provider
abstraction.

For `retrieval_mode = "dense"` (Phase 9's original, unchanged
behavior), that's the whole story: the provider's ranked hits are
persisted directly. For `retrieval_mode = "hybrid"` (Phase 10), a
second, independent BM25 sparse search (`retrieval_worker.bm25`) runs
over the same chunk_set's chunk texts, and the two rank lists are
fused (`retrieval_worker.fusion`) before persisting — both retrievers
are asked for a candidate pool larger than `top_k`
(docs/02-architecture.md section 60) so fusion has real candidates to
rank, not just each side's already-truncated top_k.

Raw SQL via a sync SQLAlchemy session, same as every other worker
package — this worker package is independently deployable and never
imports backend ORM models. It does import `index_worker.providers`
directly (not promoted to `common`, unlike the embedding providers) —
an inconsistency inherited from how Phase 9 first wired this up, kept
as-is here rather than refactored mid-phase.

Phase 11 (query understanding, docs/02-architecture.md sections 51-55)
adds an opt-in preprocessing pass (`Retrieval.query_understanding_enabled`,
default False — unset behaves exactly as Phases 9-10 did). When
enabled: the query is classified, rewritten, and expanded into
`query_variants` (`[rewritten_query_text]` alone when the LLM path
isn't configured/fails — see `query_understanding.expander`), and a
metadata filter is auto-extracted and merged under the caller-supplied
`metadata_filter` (caller wins on key conflicts, since an explicit
filter should never be silently overridden by a guess). Every
retriever call below fans out across `query_variants` (a single-item
list containing the original query text when query understanding is
off, so the loop runs exactly once and reproduces pre-Phase-11
behavior byte for byte).

Phase 12 (advanced retrieval) inserts three more opt-in stages between
"fuse" and "persist", plus a fourth alternate fusion strategy:

- `fusion_method = "rag_fusion"` (docs/02-architecture.md section 103):
  instead of collapsing each retriever's per-variant lists to one
  max-score-merged list *before* fusing dense against sparse (Phase
  10/11's approach), every per-variant per-retriever list is kept
  separate and N-way RRF-fused at once (`fusion.reciprocal_rank_fusion_multi`).
  Requires `query_understanding_enabled=True` (validated by the
  backend) since fusing multiple query variants is the entire point —
  with only one variant it degenerates to plain RRF, which the
  cheaper `"rrf"` option already covers.
- `expand_to_parent` (section 63): remaps each result's matched chunk
  to its `parent_chunk_id` when one exists (`parent_expansion.expand`),
  merging duplicates that land on the same parent by keeping the
  highest-scoring one.
- `use_mmr`/`mmr_lambda` (section 62): replaces plain
  sort-and-truncate-to-top_k with a greedy Maximum Marginal Relevance
  selection (`retrieval_worker.mmr`) over each candidate's real
  embedding vector, trading relevance against diversity.
- `compress_context` (section 75): after the final top_k is chosen,
  compresses each result's chunk text down to its query-relevant
  sentences (`retrieval_worker.compression`) and persists that
  alongside (not instead of) the original in `RetrievalResult.compressed_text`.

Phase 13 (reranking, docs/02-architecture.md sections 71-74) inserts a
fourth stage between "parent-child expand" and "MMR select/truncate":
`rerank_enabled`/`reranker_provider` re-score every candidate still in
the pool with a real cross-encoder (`retrieval_worker.reranking`) that
sees the (query, chunk_text) pair jointly, then re-sort by that score.
The candidate pool widens further when reranking is on (there must be
more than `top_k` candidates left for reranking to meaningfully
reorder). `rerank_score` is persisted *alongside* `score` (never
overwriting it, same pattern `dense_score`/`sparse_score` established)
so both signals stay independently inspectable; MMR (if also enabled)
uses `rerank_score` as its relevance term instead of `score` once
reranking has run, since it's the more accurate signal at that point.
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
from retrieval_worker import bm25, compression, fusion, mmr, parent_expansion
from retrieval_worker.query_understanding import classifier, expander, filter_extractor, rewriter
from retrieval_worker.reranking import factory as reranking_factory

logger = get_logger(__name__)

_FILTERABLE_CHUNK_COLUMNS = {"heading", "page", "language"}
_DEFAULT_DENSE_WEIGHT = 0.7
_DEFAULT_SPARSE_WEIGHT = 0.3
_DEFAULT_RRF_K = 60
_DEFAULT_MMR_LAMBDA = 0.7


def _fail(session, retrieval_id: str, message: str) -> None:
    session.execute(
        text(
            "UPDATE retrievals SET status = 'FAILED', status_message = :message, "
            "updated_at = :now WHERE id = :id"
        ),
        {"message": message[:500], "now": datetime.now(UTC), "id": retrieval_id},
    )
    session.commit()


def _fetch_chunk_texts(
    session, chunk_set_id, metadata_filter: dict | None
) -> list[tuple[str, str]]:
    filter_clauses = []
    filter_params: dict = {}
    for key, value in (metadata_filter or {}).items():
        if key not in _FILTERABLE_CHUNK_COLUMNS:
            continue
        filter_clauses.append(f"{key} = :filter_{key}")
        filter_params[f"filter_{key}"] = value
    filter_sql = "".join(f" AND {clause}" for clause in filter_clauses)

    rows = session.execute(
        text(
            "SELECT id, text FROM chunks "
            "WHERE chunk_set_id = :chunk_set_id AND status = 'READY'" + filter_sql
        ),
        {"chunk_set_id": chunk_set_id, **filter_params},
    ).all()
    return [(str(row.id), row.text) for row in rows]


def _merge_max(rank_lists: list[dict[str, float]]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for scores in rank_lists:
        for chunk_id, score in scores.items():
            if chunk_id not in merged or score > merged[chunk_id]:
                merged[chunk_id] = score
    return merged


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
                "r.metadata_filter, r.retrieval_mode, r.fusion_method, r.dense_weight, "
                "r.sparse_weight, r.rrf_k, r.query_understanding_enabled, "
                "r.expand_to_parent, r.use_mmr, r.mmr_lambda, r.compress_context, "
                "r.rerank_enabled, r.reranker_provider, "
                "vi.document_id, vi.provider AS index_provider, "
                "vi.namespace, ev.provider AS embed_provider, ev.model, ev.chunk_set_id "
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
        is_hybrid = row.retrieval_mode == "HYBRID"
        is_rag_fusion = row.fusion_method == "RAG_FUSION"
        # A larger candidate pool than top_k so fusion/MMR have real
        # candidates to work from, not just an already-truncated top_k
        # (docs/02-architecture.md section 60).
        pool_size = row.top_k
        if is_hybrid or is_rag_fusion or row.use_mmr:
            pool_size = max(pool_size, row.top_k * 3, 20)
        if row.rerank_enabled:
            # Reranking is only useful over a candidate set noticeably
            # wider than the final top_k (docs/02-architecture.md section
            # 71's "Top 100" example) — otherwise there's nothing left to
            # meaningfully reorder.
            pool_size = max(pool_size, row.top_k * 5, 50)

        query_intent = None
        intent_confidence = None
        rewritten_query_text = None
        generated_queries = None
        detected_metadata_filter = None
        query_variants = [row.query_text]

        if row.query_understanding_enabled:
            intent, confidence = classifier.classify(row.query_text)
            query_intent = intent.name
            intent_confidence = confidence
            rewritten_query_text = rewriter.rewrite(row.query_text)
            generated_queries = expander.expand(rewritten_query_text)
            query_variants = generated_queries
            detected_metadata_filter = filter_extractor.extract(row.query_text) or None
            if detected_metadata_filter:
                # Caller-supplied filter wins on key conflicts — an
                # explicit filter should never be silently overridden
                # by a heuristic guess.
                metadata_filter = {**detected_metadata_filter, **(metadata_filter or {})}

        start = time.perf_counter()
        try:
            embedder = get_embedding_provider(row.embed_provider, row.model)
        except Exception as exc:
            message = f"Query embedding failed: {exc}"[:500]
            _fail(session, retrieval_id, message)
            raise

        try:
            index_provider = get_index_provider(row.index_provider, session)
        except Exception as exc:
            message = f"Search failed: {exc}"[:500]
            _fail(session, retrieval_id, message)
            raise

        dense_lists: list[dict[str, float]] = []
        for variant in query_variants:
            try:
                query_vector = embedder.embed([variant])[0].vector
            except Exception as exc:
                message = f"Query embedding failed: {exc}"[:500]
                _fail(session, retrieval_id, message)
                raise

            try:
                hits = index_provider.search(
                    row.namespace, query_vector, pool_size, metric,
                    None if is_hybrid else row.score_threshold,
                    metadata_filter,
                )
            except UnsupportedMetricError as exc:
                message = str(exc)
                _fail(session, retrieval_id, message)
                logger.warning(
                    "execute_retrieval_unsupported_metric",
                    retrieval_id=retrieval_id,
                    error=message,
                )
                return {"status": "failed", "reason": message}
            except Exception as exc:
                message = f"Search failed: {exc}"[:500]
                _fail(session, retrieval_id, message)
                raise

            dense_lists.append({hit.chunk_id: hit.score for hit in hits})

        if is_hybrid:
            chunks = _fetch_chunk_texts(session, row.chunk_set_id, metadata_filter)
            sparse_lists = [
                {hit.chunk_id: hit.score for hit in bm25.search(chunks, variant, pool_size)}
                for variant in query_variants
            ]

            if is_rag_fusion:
                fused = fusion.reciprocal_rank_fusion_multi(
                    dense_lists + sparse_lists, row.rrf_k or _DEFAULT_RRF_K
                )
            elif row.fusion_method == "RRF":
                fused = fusion.reciprocal_rank_fusion(
                    _merge_max(dense_lists), _merge_max(sparse_lists), row.rrf_k or _DEFAULT_RRF_K
                )
            else:
                fused = fusion.weighted_sum(
                    _merge_max(dense_lists),
                    _merge_max(sparse_lists),
                    row.dense_weight if row.dense_weight is not None else _DEFAULT_DENSE_WEIGHT,
                    row.sparse_weight if row.sparse_weight is not None else _DEFAULT_SPARSE_WEIGHT,
                )

            if row.score_threshold is not None:
                fused = [hit for hit in fused if hit.fused_score >= row.score_threshold]

            results_pool = [
                {
                    "chunk_id": hit.chunk_id,
                    "score": hit.fused_score,
                    "dense_score": hit.dense_score,
                    "sparse_score": hit.sparse_score,
                }
                for hit in fused
            ]
        elif is_rag_fusion:
            fused = fusion.reciprocal_rank_fusion_multi(dense_lists, row.rrf_k or _DEFAULT_RRF_K)
            if row.score_threshold is not None:
                fused = [hit for hit in fused if hit.fused_score >= row.score_threshold]
            results_pool = [
                {"chunk_id": hit.chunk_id, "score": hit.fused_score, "dense_score": None,
                 "sparse_score": None}
                for hit in fused
            ]
        else:
            dense_scores = _merge_max(dense_lists)
            ranked = sorted(dense_scores.items(), key=lambda kv: kv[1], reverse=True)
            results_pool = [
                {"chunk_id": chunk_id, "score": score, "dense_score": None, "sparse_score": None}
                for chunk_id, score in ranked
            ]

        if row.expand_to_parent:
            parent_rows = session.execute(
                text("SELECT id, parent_chunk_id FROM chunks WHERE chunk_set_id = :chunk_set_id"),
                {"chunk_set_id": row.chunk_set_id},
            ).all()
            parent_map = {
                str(pr.id): (str(pr.parent_chunk_id) if pr.parent_chunk_id else None)
                for pr in parent_rows
            }
            results_pool = parent_expansion.expand(results_pool, parent_map)
            results_pool.sort(key=lambda r: r["score"], reverse=True)

        chunk_text_by_id: dict[str, str] = {}
        if row.rerank_enabled or row.compress_context:
            chunk_text_rows = session.execute(
                text("SELECT id, text FROM chunks WHERE chunk_set_id = :chunk_set_id"),
                {"chunk_set_id": row.chunk_set_id},
            ).all()
            chunk_text_by_id = {str(ctr.id): ctr.text for ctr in chunk_text_rows}

        for result in results_pool:
            result["rerank_score"] = None

        if row.rerank_enabled and results_pool:
            candidates = [
                (r["chunk_id"], chunk_text_by_id[r["chunk_id"]])
                for r in results_pool
                if r["chunk_id"] in chunk_text_by_id
            ]
            try:
                reranker = reranking_factory.get_provider(row.reranker_provider.lower())
                rerank_hits = reranker.rerank(row.query_text, candidates)
            except Exception as exc:
                message = f"Reranking failed: {exc}"[:500]
                _fail(session, retrieval_id, message)
                raise
            rerank_score_by_id = {hit.chunk_id: hit.score for hit in rerank_hits}
            for r in results_pool:
                r["rerank_score"] = rerank_score_by_id.get(r["chunk_id"])
            results_pool.sort(
                key=lambda r: r["rerank_score"] if r["rerank_score"] is not None else float("-inf"),
                reverse=True,
            )

        relevance_key = "rerank_score" if row.rerank_enabled else "score"

        if row.use_mmr and results_pool:
            vector_rows = session.execute(
                text(
                    "SELECT chunk_id, embedding::text AS embedding_text FROM embeddings "
                    "WHERE embedding_version_id = :embedding_version_id AND status = 'READY'"
                ),
                {"embedding_version_id": row.namespace},
            ).all()
            vectors = {
                str(vr.chunk_id): mmr.parse_vector_text(vr.embedding_text) for vr in vector_rows
            }
            candidates = sorted(
                (
                    mmr.RankedCandidate(chunk_id=r["chunk_id"], score=r[relevance_key])
                    for r in results_pool
                ),
                key=lambda c: c.score,
                reverse=True,
            )
            lambda_param = row.mmr_lambda if row.mmr_lambda is not None else _DEFAULT_MMR_LAMBDA
            selected = mmr.select(candidates, vectors, row.top_k, lambda_param)
            by_chunk_id = {r["chunk_id"]: r for r in results_pool}
            results = [by_chunk_id[candidate.chunk_id] for candidate in selected]
        else:
            results = results_pool[: row.top_k]

        compressed_by_chunk_id: dict[str, str] = {}
        if row.compress_context and results:
            for result in results:
                chunk_text = chunk_text_by_id.get(result["chunk_id"])
                if chunk_text:
                    compressed_by_chunk_id[result["chunk_id"]] = compression.compress(
                        chunk_text, row.query_text
                    )

        latency_ms = int((time.perf_counter() - start) * 1000)

        session.execute(
            text("DELETE FROM retrieval_results WHERE retrieval_id = :id"), {"id": retrieval_id}
        )
        for rank, result in enumerate(results, start=1):
            session.execute(
                text(
                    "INSERT INTO retrieval_results "
                    "(id, retrieval_id, chunk_id, rank, score, dense_score, sparse_score, "
                    "compressed_text, rerank_score) "
                    "VALUES (:id, :retrieval_id, :chunk_id, :rank, :score, :dense_score, "
                    ":sparse_score, :compressed_text, :rerank_score)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "retrieval_id": retrieval_id,
                    "chunk_id": result["chunk_id"],
                    "rank": rank,
                    "score": result["score"],
                    "dense_score": result["dense_score"],
                    "sparse_score": result["sparse_score"],
                    "compressed_text": compressed_by_chunk_id.get(result["chunk_id"]),
                    "rerank_score": result["rerank_score"],
                },
            )

        scores = [result["score"] for result in results]
        avg_similarity = sum(scores) / len(scores) if scores else None
        min_similarity = min(scores) if scores else None
        max_similarity = max(scores) if scores else None

        session.execute(
            text(
                "UPDATE retrievals SET status = 'COMPLETED', status_message = NULL, "
                "result_count = :count, avg_similarity = :avg, min_similarity = :min, "
                "max_similarity = :max, latency_ms = :latency, "
                "query_intent = :query_intent, intent_confidence = :intent_confidence, "
                "rewritten_query_text = :rewritten_query_text, "
                "generated_queries = :generated_queries, "
                "detected_metadata_filter = :detected_metadata_filter, "
                "updated_at = :now "
                "WHERE id = :id"
            ),
            {
                "count": len(results),
                "avg": avg_similarity,
                "min": min_similarity,
                "max": max_similarity,
                "latency": latency_ms,
                "query_intent": query_intent,
                "intent_confidence": intent_confidence,
                "rewritten_query_text": rewritten_query_text,
                "generated_queries": json.dumps(generated_queries) if generated_queries else None,
                "detected_metadata_filter": (
                    json.dumps(detected_metadata_filter) if detected_metadata_filter else None
                ),
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
        result_count=len(results),
        latency_ms=latency_ms,
    )
    return {"status": "completed", "result_count": len(results), "latency_ms": latency_ms}
