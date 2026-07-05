"""Unit tests for multi-query generation (docs/05-task.md Phase 11).

Only the no-LLM fallback path is exercised directly, for the same
reason test_query_rewriter.py does — no OPENAI_API_KEY in this dev
environment.
"""

from retrieval_worker.query_understanding.expander import expand


def test_expand_falls_back_to_single_query_without_api_key():
    assert expand("What is RAG?") == ["What is RAG?"]


def test_expand_respects_max_variants_argument():
    result = expand("What is RAG?", max_variants=5)
    assert result == ["What is RAG?"]
