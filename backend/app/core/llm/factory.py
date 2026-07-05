from app.core.config import get_settings
from app.core.llm.base import LLMProvider
from app.core.llm.providers.anthropic import AnthropicProvider
from app.core.llm.providers.gemini import GeminiProvider
from app.core.llm.providers.groq import GroqProvider
from app.core.llm.providers.ollama import OllamaProvider
from app.core.llm.providers.openai import OpenAIProvider
from app.core.llm.providers.openrouter import OpenRouterProvider

PROVIDER_NAMES = ["openai", "anthropic", "gemini", "groq", "openrouter", "ollama"]


def get_provider(name: str) -> LLMProvider:
    settings = get_settings()
    if name == "openai":
        return OpenAIProvider(settings.openai_api_key)
    if name == "anthropic":
        return AnthropicProvider(settings.anthropic_api_key)
    if name == "gemini":
        return GeminiProvider(settings.gemini_api_key)
    if name == "groq":
        return GroqProvider(settings.groq_api_key)
    if name == "openrouter":
        return OpenRouterProvider(settings.openrouter_api_key)
    if name == "ollama":
        return OllamaProvider(settings.ollama_base_url)
    raise ValueError(f"Unknown LLM provider: {name!r}")


def is_configured(name: str) -> bool:
    """Whether this provider has credentials set at all — distinct from
    `health_check()`, which also verifies the credentials/endpoint
    actually work right now (`ollama` has no credentials, so it's always
    "configured"; its health depends entirely on reachability)."""
    settings = get_settings()
    if name == "openai":
        return bool(settings.openai_api_key)
    if name == "anthropic":
        return bool(settings.anthropic_api_key)
    if name == "gemini":
        return bool(settings.gemini_api_key)
    if name == "groq":
        return bool(settings.groq_api_key)
    if name == "openrouter":
        return bool(settings.openrouter_api_key)
    if name == "ollama":
        return True
    raise ValueError(f"Unknown LLM provider: {name!r}")
