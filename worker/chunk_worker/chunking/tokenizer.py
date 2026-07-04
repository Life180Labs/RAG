"""Token counting (docs/02-architecture.md section 38 — every chunk
stores a token count). Uses tiktoken's `cl100k_base` encoding — the same
tokenizer OpenAI's GPT-3.5/4 models use — as a reasonable, real
approximation that's provider-agnostic until Phase 9 (LLM Gateway)
picks specific models, each of which may tokenize slightly differently.
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
