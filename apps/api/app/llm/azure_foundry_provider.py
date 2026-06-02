import os

from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class AzureFoundryProvider(LLMProvider):
    name = "azure_foundry"

    def __init__(self) -> None:
        missing = [
            key
            for key in (
                "AZURE_FOUNDRY_ENDPOINT",
                "AZURE_FOUNDRY_API_KEY",
                "AZURE_FOUNDRY_DEPLOYMENT_NAME",
            )
            if not os.getenv(key)
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Azure Foundry provider missing required configuration: {joined}")

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Azure Foundry network calls are not enabled in this MVP foundation")
