"""Unit tests for rule-based query intent classification (docs/05-task.md
Phase 11; docs/02-architecture.md section 51)."""

from retrieval_worker.query_understanding.classifier import classify
from retrieval_worker.query_understanding.types import QueryIntent


def test_classifies_definition():
    intent, confidence = classify("What is Retrieval Augmented Generation?")
    assert intent == QueryIntent.DEFINITION
    assert confidence > 0.5


def test_classifies_summarization():
    intent, _ = classify("Can you summarize the onboarding handbook for me?")
    assert intent == QueryIntent.SUMMARIZATION


def test_classifies_comparison():
    intent, _ = classify("What is the difference between HNSW and IVF Flat indexes?")
    assert intent == QueryIntent.COMPARISON


def test_classifies_multi_hop_reasoning():
    intent, _ = classify("Why does increasing chunk size affect retrieval recall?")
    assert intent == QueryIntent.MULTI_HOP_REASONING


def test_classifies_numerical_query():
    intent, _ = classify("How many vacation days do full-time employees get?")
    assert intent == QueryIntent.NUMERICAL_QUERY


def test_classifies_code_question():
    intent, _ = classify("Why does this function raise a null pointer exception?")
    assert intent == QueryIntent.CODE_QUESTION


def test_classifies_table_lookup():
    intent, _ = classify("What value is in the third column of the pricing table?")
    assert intent == QueryIntent.TABLE_LOOKUP


def test_classifies_policy_lookup():
    intent, _ = classify("What is the leave policy for contractors?")
    assert intent == QueryIntent.POLICY_LOOKUP


def test_classifies_conversational_followup():
    intent, _ = classify("What about sick leave?")
    assert intent == QueryIntent.CONVERSATIONAL_FOLLOWUP


def test_falls_back_to_fact_lookup_with_low_confidence():
    intent, confidence = classify("Who signed the original charter?")
    assert intent == QueryIntent.FACT_LOOKUP
    assert confidence < 0.5
