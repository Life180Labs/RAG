"""Deterministic cache key builders (docs/02-architecture.md section
101's "Cache Key" definition for the Prompt Cache).

The Retrieval Cache's key builder is *not* here — it's built and used
entirely inside `worker/retrieval_worker` (a separately deployable
package that never imports backend code, same rule every other worker
package already follows). This module only covers caches backend itself
owns: prompt/completion caching happens in `LLMService`, which lives in
this process.

Keys are a hash of exactly the inputs the architecture doc specifies —
never the raw text itself, keeping Redis keys short and avoiding leaking
prompt content into key names visible via `KEYS`/`MONITOR`/`redis-cli`.
"""

import hashlib


def _hash(*parts: str) -> str:
    joined = "\x1f".join(parts)  # unit separator: parts can contain any character, including ":"
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def hash_text(text: str) -> str:
    return _hash(text)


def prompt_cache_key(rendered_prompt: str, provider: str, model: str, context_hash: str) -> str:
    """Cache Key = Prompt Hash + Model Version + Context Hash."""
    return _hash(rendered_prompt, provider, model, context_hash)
