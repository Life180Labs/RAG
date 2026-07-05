from app.core.llm.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str | None):
        super().__init__(name="openai", base_url="https://api.openai.com/v1", api_key=api_key)
