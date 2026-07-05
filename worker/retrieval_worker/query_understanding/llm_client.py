"""Shared chat-completion helper for query rewrite/expansion (docs/05-task.md
Phase 11).

Real HTTP integration against OpenAI's chat completions API — not a
stub — reusing the same `OPENAI_API_KEY` setting Phase 7's
`OpenAIEmbeddingProvider` already gates on
(`worker/common/embedding_providers/cloud.py`), since this dev
environment has no paid key configured either. `rewriter.py` and
`expander.py` both catch `ProviderNotConfiguredError` and fall back to
a non-LLM degraded behavior rather than failing the retrieval — query
understanding is an opt-in *enhancement*, never a hard dependency.

Kept local to `retrieval_worker` (not promoted to `common`) per
CLAUDE.md's "don't design for hypothetical future requirements": no
other worker package needs a chat-completion call yet, unlike the
embedding provider promotion, which happened only once `retrieval_worker`
had a real, present-tense need to reuse it.
"""

from openai import OpenAI

from common.config import get_worker_settings

_DEFAULT_MODEL = "gpt-4o-mini"


class ProviderNotConfiguredError(Exception):
    pass


def complete(prompt: str, *, system: str, temperature: float = 0.2) -> str:
    api_key = get_worker_settings().openai_api_key
    if not api_key:
        raise ProviderNotConfiguredError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=_DEFAULT_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""
