"""Model Registry (docs/05-task.md Phase 15; docs/02-architecture.md
section 84): every model the gateway can route to is registered here —
provider, context window, per-1M-token pricing, and capability flags —
so `router.py`'s Dynamic Model Routing (section 85) and `base.py`'s
`cost_estimate` never need to special-case a specific model by name.

Pricing is a static, approximate USD-per-1M-tokens snapshot (each
provider's real published list pricing at the time this was written) —
provider pricing changes over time and this registry does not call out
to a live pricing API, so treat these as estimates for comparison
purposes, not billing-accurate figures; `cost_estimate()` is named that
way deliberately (docs/02-architecture.md section 89, "Cost Estimation").

`is_fast`/`is_reasoning` are the two capability distinctions section 85's
routing examples need that aren't derivable from context window or price
alone (a "fast" model is a qualitative product positioning, not something
computable); every other routing decision (`large_context`, `low_budget`)
is computed directly from `context_window`/pricing instead of a redundant
flag.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    context_window: int
    price_per_1m_input: float
    price_per_1m_output: float
    supports_streaming: bool = True
    supports_json_mode: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_reasoning: bool = False
    is_fast: bool = False
    is_reasoning: bool = False


_MODEL_SPECS: list[ModelSpec] = [
    ModelSpec(
        provider="openai",
        model="gpt-4o-mini",
        context_window=128_000,
        price_per_1m_input=0.15,
        price_per_1m_output=0.60,
        supports_json_mode=True,
        supports_vision=True,
        supports_function_calling=True,
        is_fast=True,
    ),
    ModelSpec(
        provider="openai",
        model="gpt-4o",
        context_window=128_000,
        price_per_1m_input=2.50,
        price_per_1m_output=10.00,
        supports_json_mode=True,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ModelSpec(
        provider="openai",
        model="o1-mini",
        context_window=128_000,
        price_per_1m_input=1.10,
        price_per_1m_output=4.40,
        supports_reasoning=True,
        is_reasoning=True,
    ),
    ModelSpec(
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        context_window=200_000,
        price_per_1m_input=0.80,
        price_per_1m_output=4.00,
        supports_vision=True,
        supports_function_calling=True,
        is_fast=True,
    ),
    ModelSpec(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        context_window=200_000,
        price_per_1m_input=3.00,
        price_per_1m_output=15.00,
        supports_vision=True,
        supports_function_calling=True,
        supports_reasoning=True,
        is_reasoning=True,
    ),
    ModelSpec(
        provider="gemini",
        model="gemini-1.5-flash",
        context_window=1_000_000,
        price_per_1m_input=0.075,
        price_per_1m_output=0.30,
        supports_json_mode=True,
        supports_vision=True,
        supports_function_calling=True,
        is_fast=True,
    ),
    ModelSpec(
        provider="gemini",
        model="gemini-1.5-pro",
        context_window=2_000_000,
        price_per_1m_input=1.25,
        price_per_1m_output=5.00,
        supports_json_mode=True,
        supports_vision=True,
        supports_function_calling=True,
    ),
    ModelSpec(
        provider="groq",
        model="llama-3.1-8b-instant",
        context_window=128_000,
        price_per_1m_input=0.05,
        price_per_1m_output=0.08,
        is_fast=True,
    ),
    ModelSpec(
        provider="groq",
        model="llama-3.3-70b-versatile",
        context_window=128_000,
        price_per_1m_input=0.59,
        price_per_1m_output=0.79,
    ),
    ModelSpec(
        provider="openrouter",
        model="meta-llama/llama-3.3-70b-instruct",
        context_window=128_000,
        price_per_1m_input=0.35,
        price_per_1m_output=0.40,
    ),
    ModelSpec(
        provider="ollama",
        model="deepseek-r1:1.5b",
        context_window=131_072,
        price_per_1m_input=0.0,
        price_per_1m_output=0.0,
        supports_reasoning=True,
        is_reasoning=True,
    ),
]

MODEL_REGISTRY: dict[tuple[str, str], ModelSpec] = {
    (spec.provider, spec.model): spec for spec in _MODEL_SPECS
}

DEFAULT_MODEL_BY_PROVIDER: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "gemini": "gemini-1.5-flash",
    "groq": "llama-3.1-8b-instant",
    "openrouter": "meta-llama/llama-3.3-70b-instruct",
    "ollama": "deepseek-r1:1.5b",
}


def get_model_spec(provider: str, model: str) -> ModelSpec:
    spec = MODEL_REGISTRY.get((provider, model))
    if spec is None:
        raise KeyError(f"No registered model {model!r} for provider {provider!r}.")
    return spec


def list_models() -> list[ModelSpec]:
    return list(MODEL_REGISTRY.values())
