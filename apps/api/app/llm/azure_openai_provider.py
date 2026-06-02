import os

from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class AzureOpenAIProvider(LLMProvider):
    name = "azure_openai"

    def __init__(self) -> None:
        missing = [
            key
            for key in (
                "AZURE_OPENAI_ENDPOINT",
                "AZURE_OPENAI_API_KEY",
                "AZURE_OPENAI_DEPLOYMENT_NAME",
            )
            if not os.getenv(key)
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Azure OpenAI provider missing required configuration: {joined}")

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Azure OpenAI network calls are not enabled in this MVP foundation")
