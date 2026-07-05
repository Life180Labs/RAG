"""Query intent classification (docs/05-task.md Phase 11;
docs/02-architecture.md section 51 Query Understanding).

Rule-based (keyword/regex over the fixed 10-way taxonomy the
architecture doc specifies), not a trained classifier — the same
"real but deliberately scoped" choice Phase 10 made for BM25:
deterministic, fully unit-testable without any external dependency or
paid API key, and the taxonomy's categories each have clear lexical
signals (comparison queries say "vs"/"compare", code questions
mention "function"/"error", etc.).

Checks run in a fixed priority order (most specific first) so a query
matching multiple signals (e.g. "compare the policy on X vs Y", which
mentions both "policy" and "vs") lands on the more specific
comparison intent rather than the generic policy-lookup one. Anything
matching no rule falls back to FACT_LOOKUP (the taxonomy's most
generic bucket) with low confidence rather than raising — a query
understanding failure must never block retrieval.
"""

import re

from retrieval_worker.query_understanding.types import QueryIntent

_MATCHED_CONFIDENCE = 0.9
_FALLBACK_CONFIDENCE = 0.4

_RULES: list[tuple[QueryIntent, re.Pattern]] = [
    (
        QueryIntent.CONVERSATIONAL_FOLLOWUP,
        re.compile(r"^\s*(what about|how about|and what about|what of)\b", re.IGNORECASE),
    ),
    (
        QueryIntent.CODE_QUESTION,
        re.compile(
            r"\b(function|method|class|exception|stack trace|traceback|syntax|"
            r"compile|variable|code snippet|api call|null pointer|segfault)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QueryIntent.TABLE_LOOKUP,
        re.compile(r"\b(table|row|column|cell|spreadsheet)\b", re.IGNORECASE),
    ),
    (
        QueryIntent.POLICY_LOOKUP,
        re.compile(
            r"\b(policy|policies|compliance|regulation|sop|procedure|guideline)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QueryIntent.COMPARISON,
        re.compile(
            r"\b(vs\.?|versus|compare|comparison|difference between|which is better)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QueryIntent.MULTI_HOP_REASONING,
        re.compile(
            r"\b(why does .* (affect|impact|cause)|impact of .* on|"
            r"relationship between|leads? to|as a result of)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QueryIntent.NUMERICAL_QUERY,
        re.compile(
            r"\b(how much|how many|percentage|percent|total cost|number of)\b|\d",
            re.IGNORECASE,
        ),
    ),
    (
        QueryIntent.SUMMARIZATION,
        re.compile(
            r"\b(summarize|summary|summarise|overview|tl;?dr|key points|in short)\b",
            re.IGNORECASE,
        ),
    ),
    (
        QueryIntent.DEFINITION,
        re.compile(
            r"^\s*(what is|what are|define|definition of|meaning of)\b", re.IGNORECASE
        ),
    ),
]


def classify(query_text: str) -> tuple[QueryIntent, float]:
    for intent, pattern in _RULES:
        if pattern.search(query_text):
            return intent, _MATCHED_CONFIDENCE
    return QueryIntent.FACT_LOOKUP, _FALLBACK_CONFIDENCE
