"""Token counting, shared across worker packages (docs/06-rule.md — never
duplicate business logic). Uses tiktoken's `cl100k_base` encoding — the
same tokenizer OpenAI's GPT-3.5/4 models use — as a reasonable, real,
provider-agnostic approximation for both chunk token counts
(docs/02-architecture.md section 38) and embedding cost/usage tracking
(section 40), until each downstream provider's own tokenizer is wired in.
"""

from functools import lru_cache

import tiktoken


@lru_cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_encoding().encode(text))
