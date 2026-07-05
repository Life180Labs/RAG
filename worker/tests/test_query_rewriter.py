"""Unit tests for query rewriting (docs/05-task.md Phase 11).

Only the no-LLM fallback path is exercised directly — this dev
environment has no OPENAI_API_KEY configured (same convention as
worker/tests/test_embedding_providers.py's cloud provider tests), so
the real LLM call is never made in CI/local runs; the fallback is what
`execute_retrieval` actually exercises here.
"""

from retrieval_worker.query_understanding.rewriter import rewrite


def test_rewrite_falls_back_to_normalized_original_without_api_key():
    assert rewrite("  what about   sick leave?  ") == "what about sick leave?"


def test_rewrite_collapses_internal_whitespace():
    assert rewrite("what\nis\tthe   policy") == "what is the policy"
