"""Multi-query generation (docs/05-task.md Phase 11; docs/02-architecture.md
section 54 Multi Query Generation).

Generates up to `max_variants` alternative phrasings via one LLM call,
always including the (rewritten) query itself as the first variant so
callers can fan out retrieval uniformly whether or not the LLM path
produced anything extra. Falls back to `[query_text]` alone —
single-query behavior, unchanged from Phase 9/10 — when
`OPENAI_API_KEY` isn't configured or the call fails; this is the same
documented degradation `rewriter.py` uses, not a bug.
"""

from common.logging import get_logger
from retrieval_worker.query_understanding.llm_client import ProviderNotConfiguredError, complete

logger = get_logger(__name__)

_SYSTEM_PROMPT_TEMPLATE = (
    "Generate {n} alternative phrasings of the user's search query that "
    "preserve its exact meaning, to maximize recall when each is used as "
    "an independent retrieval query. Reply with exactly {n} lines, one "
    "query per line, no numbering, no bullet points, no commentary."
)


def expand(query_text: str, max_variants: int = 3) -> list[str]:
    variants = [query_text]
    try:
        raw = complete(query_text, system=_SYSTEM_PROMPT_TEMPLATE.format(n=max_variants))
    except ProviderNotConfiguredError:
        return variants
    except Exception as exc:
        logger.warning("query_expansion_failed", error=str(exc))
        return variants

    generated = [line.strip(" -\t") for line in raw.splitlines() if line.strip()]

    seen = {query_text.strip().lower()}
    for candidate in generated[:max_variants]:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            variants.append(candidate)
    return variants
