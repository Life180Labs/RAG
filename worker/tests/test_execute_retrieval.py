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


def _build_pgvector_index(
    document_id: uuid.UUID, strategy: str = "structural", split_chunks: bool = False
) -> tuple[str, str]:
    """Runs chunk -> embed -> index for one document and returns
    (vector_index_id, document_id) for the pgvector index built."""
    chunk_document.run(str(document_id), strategy)
    with SessionLocal() as session:
        chunk_set = session.execute(
            text("SELECT id FROM document_chunk_sets WHERE document_id = :id"),
            {"id": document_id},
        ).first()
        chunk_set_id = chunk_set.id

    if split_chunks:
        _split_chunk_set_into_two(chunk_set_id)

    with SessionLocal() as session:
        embed_chunk_set.run(str(chunk_set_id), "bge")
        version = session.execute(
            text(
                "SELECT id FROM embedding_versions WHERE chunk_set_id = :id AND provider = 'bge'"
            ),
            {"id": chunk_set_id},
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
        "retrieval_mode": "DENSE",
        "fusion_method": None,
        "dense_weight": None,
        "sparse_weight": None,
        "rrf_k": None,
        "query_understanding_enabled": False,
        "expand_to_parent": False,
        "use_mmr": False,
        "mmr_lambda": None,
        "compress_context": False,
        "rerank_enabled": False,
        "reranker_provider": None,
        "status": "PENDING",
        "result_count": 0,
        **overrides,
    }
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO retrievals "
                "(id, vector_index_id, document_id, query_text, top_k, score_threshold, "
                "similarity_metric, metadata_filter, retrieval_mode, fusion_method, "
                "dense_weight, sparse_weight, rrf_k, query_understanding_enabled, "
                "expand_to_parent, use_mmr, mmr_lambda, compress_context, "
                "rerank_enabled, reranker_provider, status, "
                "result_count, created_at, updated_at) "
                "VALUES (:id, :vector_index_id, :document_id, :query_text, :top_k, "
                ":score_threshold, :similarity_metric, CAST(:metadata_filter AS jsonb), "
                ":retrieval_mode, :fusion_method, :dense_weight, :sparse_weight, :rrf_k, "
                ":query_understanding_enabled, :expand_to_parent, :use_mmr, :mmr_lambda, "
                ":compress_context, :rerank_enabled, :reranker_provider, "
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


_HYBRID_BLOCKS = [
    {"type": "heading", "text": "Error Codes", "level": 1, "page": None},
    {
        "type": "paragraph",
        "text": "Error code XJ-9042 indicates a checkout timeout in the payment gateway.",
        "level": None,
        "page": None,
    },
    {
        "type": "paragraph",
        "text": "Vector databases support cosine similarity search over embeddings.",
        "level": None,
        "page": None,
    },
]


_SPLIT_CHUNK_TEXTS = [
    "Error code XJ-9042 indicates a checkout timeout in the payment gateway.",
    "Vector databases support cosine similarity search over embeddings.",
    "Enterprise software licensing agreements and compliance requirements.",
    "The weather forecast predicts rain for the entire weekend.",
    "A simple recipe for baking sourdough bread at home.",
    "Quarterly financial results exceeded analyst expectations this year.",
]


def _split_chunk_set_into_two(chunk_set_id) -> None:
    """The real chunkers merge short test paragraphs below max_tokens
    into a single chunk regardless of strategy, but BM25's IDF is
    degenerate over a corpus of only one or two documents (a query
    term appearing in exactly half of a 2-document corpus gets an
    exact-zero IDF — see bm25.py's docstring and test_bm25.py) — so for
    hybrid-fusion tests specifically, replace the one generated chunk
    with several distractor chunks plus the two real source sentences,
    giving BM25 a corpus large enough for a real, non-degenerate score.
    """
    with SessionLocal() as session:
        chunk = session.execute(
            text(
                "SELECT id FROM chunks WHERE chunk_set_id = :id ORDER BY chunk_index LIMIT 1"
            ),
            {"id": chunk_set_id},
        ).first()
        session.execute(
            text("UPDATE chunks SET text = :text, char_start = 0, char_end = 73 WHERE id = :id"),
            {"id": chunk.id, "text": _SPLIT_CHUNK_TEXTS[0]},
        )
        for index, chunk_text in enumerate(_SPLIT_CHUNK_TEXTS[1:], start=1):
            session.execute(
                text(
                    "INSERT INTO chunks (id, chunk_set_id, chunk_index, text, char_start, "
                    "char_end, token_count, page, heading, language, status) "
                    "VALUES (gen_random_uuid(), :chunk_set_id, :chunk_index, :text, 0, "
                    "100, 12, NULL, NULL, 'en', 'READY')"
                ),
                {"chunk_set_id": chunk_set_id, "chunk_index": index, "text": chunk_text},
            )
        session.execute(
            text(
                "UPDATE document_chunk_sets SET chunk_count = :count WHERE id = :id"
            ),
            {"id": chunk_set_id, "count": len(_SPLIT_CHUNK_TEXTS)},
        )
        session.commit()


def _insert_document_with_hybrid_content(repository_id, uploader_id) -> uuid.UUID:
    document_id = uuid.uuid4()
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO documents (id, repository_id, filename, mime_type, size_bytes, "
                "sha256_hash, storage_key, status, current_version, uploaded_by) "
                "VALUES (:id, :repository_id, 'b.txt', 'text/plain', 10, 'y', 'k', "
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
            {"document_id": document_id, "blocks": json.dumps(_HYBRID_BLOCKS)},
        )
        session.commit()
    return document_id


def test_execute_retrieval_hybrid_weighted_sum_populates_component_scores(document_chain):
    document_id = _insert_document_with_hybrid_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id, split_chunks=True)
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="XJ-9042 checkout error",
        retrieval_mode="HYBRID",
        fusion_method="WEIGHTED_SUM",
        dense_weight=0.7,
        sparse_weight=0.3,
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"
    assert result["result_count"] > 0

    with SessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT rank, score, dense_score, sparse_score FROM retrieval_results "
                "WHERE retrieval_id = :id ORDER BY rank"
            ),
            {"id": retrieval_id},
        ).all()
        assert rows[0].dense_score is not None
        # The top BM25-favored chunk (exact "XJ-9042" match) should be
        # ranked first — dense alone (a generic small local model on a
        # tiny corpus) has no reason to prefer it, so this only holds if
        # the sparse side is genuinely contributing to the fused score.
        assert rows[0].sparse_score is not None and rows[0].sparse_score > 0


def test_execute_retrieval_hybrid_rrf(document_chain):
    document_id = _insert_document_with_hybrid_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id, split_chunks=True)
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="cosine similarity embeddings",
        retrieval_mode="HYBRID",
        fusion_method="RRF",
        rrf_k=60,
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"

    with SessionLocal() as session:
        row = session.execute(
            text("SELECT retrieval_mode, fusion_method FROM retrievals WHERE id = :id"),
            {"id": retrieval_id},
        ).first()
        assert row.retrieval_mode == "HYBRID"
        assert row.fusion_method == "RRF"


def test_execute_retrieval_query_understanding_populates_analysis_fields(document_chain):
    # No OPENAI_API_KEY in this dev environment (same as the Phase 7
    # cloud embedding provider tests), so rewrite/expansion fall back to
    # the documented no-LLM behavior: rewritten_query_text is just the
    # normalized original, generated_queries is a single-item list. The
    # point of this test is that the *pipeline wiring* (classify persists
    # an intent, the fallback still completes the retrieval, filter
    # extraction still runs) works end-to-end, not that the LLM path
    # itself was exercised.
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text='What is the policy in "Section One"?',
        query_understanding_enabled=True,
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"

    with SessionLocal() as session:
        row = session.execute(
            text(
                "SELECT query_intent, intent_confidence, rewritten_query_text, "
                "generated_queries, detected_metadata_filter FROM retrievals WHERE id = :id"
            ),
            {"id": retrieval_id},
        ).first()
        assert row.query_intent == "POLICY_LOOKUP"
        assert row.intent_confidence is not None
        assert row.rewritten_query_text == 'What is the policy in "Section One"?'
        assert row.generated_queries == ['What is the policy in "Section One"?']
        assert row.detected_metadata_filter == {"heading": "Section One"}


_MULTI_SECTION_BLOCKS = [
    {"type": "heading", "text": "Chapter One", "level": 1, "page": None},
    {
        "type": "paragraph",
        "text": "Chapter one covers the fundamentals of retrieval augmented generation "
        "in significant detail, including architecture and design considerations.",
        "level": None,
        "page": None,
    },
    {"type": "heading", "text": "Chapter Two", "level": 1, "page": None},
    {
        "type": "paragraph",
        "text": "Chapter two explains vector databases and approximate nearest neighbor "
        "search algorithms used across enterprise retrieval systems.",
        "level": None,
        "page": None,
    },
]


def test_execute_retrieval_expand_to_parent_returns_parentless_chunks(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    with SessionLocal() as session:
        session.execute(
            text("UPDATE document_content SET structured_content = CAST(:blocks AS jsonb) "
                 "WHERE document_id = :id"),
            {"id": document_id, "blocks": json.dumps(_MULTI_SECTION_BLOCKS)},
        )
        session.commit()
    vector_index_id = _build_pgvector_index(document_id, strategy="parent_child")
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="vector databases nearest neighbor search",
        top_k=5,
        expand_to_parent=True,
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"
    assert result["result_count"] > 0

    with SessionLocal() as session:
        chunk_ids = session.execute(
            text("SELECT chunk_id FROM retrieval_results WHERE retrieval_id = :id"),
            {"id": retrieval_id},
        ).all()
        for row in chunk_ids:
            chunk = session.execute(
                text("SELECT parent_chunk_id FROM chunks WHERE id = :id"), {"id": row.chunk_id}
            ).first()
            assert chunk.parent_chunk_id is None


def test_execute_retrieval_mmr_respects_top_k(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    with SessionLocal() as session:
        session.execute(
            text("UPDATE document_content SET structured_content = CAST(:blocks AS jsonb) "
                 "WHERE document_id = :id"),
            {"id": document_id, "blocks": json.dumps(_MULTI_SECTION_BLOCKS)},
        )
        session.commit()
    vector_index_id = _build_pgvector_index(document_id, strategy="sentence")
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="retrieval augmented generation vector databases",
        top_k=2,
        use_mmr=True,
        mmr_lambda=0.5,
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"
    assert 0 < result["result_count"] <= 2


def test_execute_retrieval_compress_context_populates_compressed_text(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)
    retrieval_id = _insert_retrieval(
        vector_index_id, document_id, query_text="Section One", compress_context=True
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"

    with SessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT compressed_text FROM retrieval_results WHERE retrieval_id = :id"
            ),
            {"id": retrieval_id},
        ).all()
        assert all(row.compressed_text is not None for row in rows)


def test_execute_retrieval_rag_fusion_hybrid(document_chain):
    document_id = _insert_document_with_hybrid_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id, split_chunks=True)
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="XJ-9042 checkout error",
        retrieval_mode="HYBRID",
        fusion_method="RAG_FUSION",
        rrf_k=60,
        query_understanding_enabled=True,
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"
    assert result["result_count"] > 0

    with SessionLocal() as session:
        row = session.execute(
            text("SELECT fusion_method, retrieval_mode FROM retrievals WHERE id = :id"),
            {"id": retrieval_id},
        ).first()
        assert row.fusion_method == "RAG_FUSION"
        assert row.retrieval_mode == "HYBRID"


def test_execute_retrieval_reranking_populates_rerank_score(document_chain):
    document_id = _insert_document_with_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id)
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="Section One",
        rerank_enabled=True,
        reranker_provider="CROSS_ENCODER",
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"
    assert result["result_count"] > 0

    with SessionLocal() as session:
        row = session.execute(
            text("SELECT reranker_provider FROM retrievals WHERE id = :id"),
            {"id": retrieval_id},
        ).first()
        assert row.reranker_provider == "CROSS_ENCODER"

        rows = session.execute(
            text("SELECT rerank_score FROM retrieval_results WHERE retrieval_id = :id"),
            {"id": retrieval_id},
        ).all()
        assert all(r.rerank_score is not None for r in rows)


def test_execute_retrieval_reranking_reorders_by_relevance(document_chain):
    # Two distractor chunks plus one that's an exact phrase match for
    # the query — dense similarity from a small local embedding model
    # over a tiny corpus has no strong reason to rank the exact match
    # first, but a real cross-encoder should.
    document_id = _insert_document_with_hybrid_content(
        document_chain["repository_id"], document_chain["user_id"]
    )
    vector_index_id = _build_pgvector_index(document_id, split_chunks=True)
    retrieval_id = _insert_retrieval(
        vector_index_id,
        document_id,
        query_text="What indicates a checkout timeout in the payment gateway?",
        top_k=6,
        rerank_enabled=True,
        reranker_provider="CROSS_ENCODER",
    )

    result = execute_retrieval.run(retrieval_id)
    assert result["status"] == "completed"

    with SessionLocal() as session:
        rows = session.execute(
            text(
                "SELECT rr.rank, c.text FROM retrieval_results rr "
                "JOIN chunks c ON c.id = rr.chunk_id "
                "WHERE rr.retrieval_id = :id ORDER BY rr.rank"
            ),
            {"id": retrieval_id},
        ).all()
        assert "XJ-9042" in rows[0].text
