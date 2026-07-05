"""Query condensation (docs/05-task.md Phase 16; docs/02-architecture.md
section 95's own example: "What about contractors?" is meaningless
without the prior turn — resolving that reference is real language
understanding, not something a keyword-overlap heuristic can do. Phase
11's query understanding rewrites/expands a *single* query for clarity;
it never sees prior turns at all, so it structurally cannot solve this —
this is a genuinely different problem needing the real LLM Gateway
Phase 15 just built, not a re-implementation of Phase 11 under a new name.

Failure here degrades gracefully: if the gateway can't produce a
condensed query for any reason (no provider configured/reachable,
transient failure), the turn proceeds with the raw, un-condensed query
rather than failing the whole conversation turn — a worse retrieval
query is better than no answer at all.
"""

from app.core.llm.base import LLMMessage, ProviderRequestOptions
from app.core.llm.gateway import LLMGateway
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You rewrite a user's follow-up question into a standalone question, using the "
    "conversation history for context. Respond with ONLY the rewritten standalone "
    "question and nothing else — no explanation, no preamble."
)


async def condense_query(gateway: LLMGateway, history_text: str, new_query: str) -> str:
    if not history_text.strip():
        return new_query

    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(
            role="user",
            content=(
                f"Conversation history:\n{history_text}\n\n"
                f"Follow-up question: {new_query}\n\nStandalone question:"
            ),
        ),
    ]
    try:
        result, _, _, _ = await gateway.generate(
            messages, routing_hint="fast", options=ProviderRequestOptions(temperature=0.0)
        )
    except Exception as exc:  # noqa: BLE001 - any gateway failure degrades to the raw query
        logger.warning("query_condensation_failed", error=str(exc))
        return new_query

    condensed = result.text.strip()
    return condensed or new_query
