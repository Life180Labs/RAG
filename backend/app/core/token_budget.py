"""Token Budget Manager (docs/05-task.md Phase 14; docs/02-architecture.md
section 76).

Allocates a fixed `model_context_window` across System Prompt /
Conversation / Retrieved Context / User Query / Response Budget, exactly
the section 76 diagram. `count_tokens` uses `tiktoken`'s `cl100k_base`
encoding — not the exact tokenizer of every downstream LLM provider
(Phase 15), but a real, deterministic, model-agnostic count rather than a
length-based heuristic, which is what "reproducible" (this phase's
Acceptance Criteria) requires: the same text always yields the same
count regardless of which provider eventually serves the completion.

`conversation_tokens` is always 0 here — persistent conversation memory
is Phase 16 (`docs/05-task.md`), not built yet — but the budget still
subtracts it (a no-op subtraction of zero) so Phase 16 can populate it
without touching this allocation formula.

Never exceeds the model's context window: if System Prompt + Conversation
+ User Query + Response Reserve alone already consume the full budget,
the remaining context budget floors at 0 rather than going negative —
the Context Window Builder then legitimately includes zero chunks
(a build failure worth surfacing to the caller, not something this
module should paper over by ignoring the reserve).
"""

from functools import lru_cache

import tiktoken

DEFAULT_RESPONSE_RESERVE_TOKENS = 1024

_ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_encoding().encode(text))


def available_context_tokens(
    *,
    model_context_window: int,
    system_prompt_tokens: int,
    conversation_tokens: int,
    query_tokens: int,
    response_reserve_tokens: int = DEFAULT_RESPONSE_RESERVE_TOKENS,
) -> int:
    used = system_prompt_tokens + conversation_tokens + query_tokens + response_reserve_tokens
    return max(model_context_window - used, 0)
