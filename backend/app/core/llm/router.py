"""Dynamic Model Routing (docs/05-task.md Phase 15; docs/02-architecture.md
section 85): picks a model automatically from a coarse `routing_hint`
rather than requiring the caller to already know which provider/model is
"fast" or "cheap". An explicit `provider`+`model` always wins outright —
routing only kicks in when the caller doesn't already know what it wants.

Each hint maps to something genuinely computable from `registry.py`'s
`ModelSpec` fields, not a guess:
- `"fast"` / `"reasoning"` — the two qualitative capability flags the
  registry stores explicitly, since "fast" and "reasoning" are product
  positioning, not something derivable from context window or price.
- `"large_context"` — the model with the largest `context_window`.
- `"low_budget"` — the model with the lowest combined per-1M-token price.
- `"offline"` — the (self-hosted, zero-cost) `ollama` entry specifically.
"""

from typing import Literal

from app.core.llm.registry import DEFAULT_MODEL_BY_PROVIDER, ModelSpec, get_model_spec, list_models

RoutingHint = Literal["fast", "reasoning", "large_context", "low_budget", "offline"]

_DEFAULT_PROVIDER = "openai"


class NoMatchingModelError(ValueError):
    pass


def select_model(
    *,
    routing_hint: RoutingHint | None = None,
    explicit_provider: str | None = None,
    explicit_model: str | None = None,
) -> ModelSpec:
    if explicit_provider and explicit_model:
        try:
            return get_model_spec(explicit_provider, explicit_model)
        except KeyError as exc:
            raise NoMatchingModelError(str(exc)) from exc

    candidates = list_models()

    if routing_hint is None:
        return get_model_spec(_DEFAULT_PROVIDER, DEFAULT_MODEL_BY_PROVIDER[_DEFAULT_PROVIDER])

    if routing_hint == "fast":
        fast_models = [m for m in candidates if m.is_fast]
        if not fast_models:
            raise NoMatchingModelError("No registered model is flagged is_fast.")
        return min(fast_models, key=lambda m: m.price_per_1m_input + m.price_per_1m_output)

    if routing_hint == "reasoning":
        reasoning_models = [m for m in candidates if m.is_reasoning]
        if not reasoning_models:
            raise NoMatchingModelError("No registered model is flagged is_reasoning.")
        return reasoning_models[0]

    if routing_hint == "large_context":
        return max(candidates, key=lambda m: m.context_window)

    if routing_hint == "low_budget":
        return min(candidates, key=lambda m: m.price_per_1m_input + m.price_per_1m_output)

    if routing_hint == "offline":
        return get_model_spec("ollama", DEFAULT_MODEL_BY_PROVIDER["ollama"])

    raise NoMatchingModelError(f"Unknown routing_hint: {routing_hint!r}")
