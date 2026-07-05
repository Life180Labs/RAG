from app.core.llm.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str | None):
        super().__init__(
            name="openrouter", base_url="https://openrouter.ai/api/v1", api_key=api_key
        )
