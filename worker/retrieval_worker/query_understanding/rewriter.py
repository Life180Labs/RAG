"""Query rewriting (docs/05-task.md Phase 11; docs/02-architecture.md
section 53 Query Rewriting).

The architecture doc's own example rewrites an incomplete query using
prior *conversation context* ("What about sick leave?" + "Employee
Handbook" -> "What is the sick leave policy described in the employee
handbook?"). This system has no conversation/session model yet (see
docs/02-architecture.md section 95, Conversation Memory Architecture —
a separate, later architecture concern with no backing table today),
so Phase 11's rewrite operates on the single query in isolation: an
LLM call turns a terse/incomplete query into a complete, self-contained
one using only general-purpose judgment, not prior turns. Multi-turn
context-aware rewriting is left for whichever phase actually adds
conversation history.

Falls back to whitespace/punctuation normalization (no rewrite) when
`OPENAI_API_KEY` isn't configured, or if the API call fails for any
reason — a query understanding failure must never block retrieval.
"""

import re

from common.logging import get_logger
from retrieval_worker.query_understanding.llm_client import ProviderNotConfiguredError, complete

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You rewrite a user's search query into a single, complete, "
    "self-contained question suitable for document retrieval. Preserve "
    "the original meaning and intent exactly — do not answer the "
    "question, do not add facts. Reply with only the rewritten query "
    "text and nothing else."
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def rewrite(query_text: str) -> str:
    normalized = _normalize(query_text)
    try:
        rewritten = complete(normalized, system=_SYSTEM_PROMPT)
    except ProviderNotConfiguredError:
        return normalized
    except Exception as exc:
        logger.warning("query_rewrite_failed", error=str(exc))
        return normalized

    rewritten = _normalize(rewritten)
    return rewritten or normalized
