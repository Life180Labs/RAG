"""Conversation Summarization (docs/05-task.md Phase 16;
docs/02-architecture.md section 98): a real LLM call that compacts raw
message history into a short summary once it grows past a token
threshold, so context assembly for later turns stays bounded instead of
including every message verbatim forever.

Unlike `condensation.py`, a summarization failure is not silently
swallowed here — raising lets `ConversationService` simply skip
summarizing *this* turn and try again on the next one, rather than
persisting a fabricated or empty summary that would be indistinguishable
from a real one later.
"""

from app.core.llm.base import LLMMessage, ProviderRequestOptions
from app.core.llm.gateway import LLMGateway

_SYSTEM_PROMPT = (
    "Summarize the following conversation concisely in the third person, in under 150 "
    "words. Preserve key facts, decisions, and any stated user preferences. Respond with "
    "ONLY the summary."
)


async def summarize_messages(
    gateway: LLMGateway,
    messages_text: str,
    credential_overrides: dict[str, str] | None = None,
) -> str:
    messages = [
        LLMMessage(role="system", content=_SYSTEM_PROMPT),
        LLMMessage(role="user", content=messages_text),
    ]
    result, _, _, _ = await gateway.generate(
        messages,
        routing_hint="fast",
        options=ProviderRequestOptions(temperature=0.0),
        credential_overrides=credential_overrides,
    )
    return result.text.strip()
