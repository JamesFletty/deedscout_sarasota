from collections.abc import Callable

from app.core.config import Settings, get_settings
from app.llm.azure_foundry_provider import AzureFoundryProvider
from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.llm.github_models_provider import GitHubModelsProvider
from app.llm.mock_provider import MockProvider
from app.llm.ollama_provider import OllamaProvider


class LLMRouter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.calls_used = 0
        self.provider = self._build_provider(self.settings.llm_provider)

    def complete(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        request = LLMRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            require_json=self.settings.llm_require_json,
            max_input_chars=self.settings.llm_max_input_chars,
        )
        return self.complete_request(request)

    def complete_request(self, request: LLMRequest) -> LLMResponse:
        if self.calls_used >= self.settings.llm_max_calls_per_batch:
            raise ValueError("LLM call limit exceeded for this batch")
        response = self.provider.complete(request)
        self.calls_used += 1
        return response

    def _build_provider(self, provider_name: str) -> LLMProvider:
        providers: dict[str, Callable[[], LLMProvider]] = {
            "mock": MockProvider,
            "azure_openai": AzureOpenAIProvider,
            "azure_foundry": AzureFoundryProvider,
            "github_models": GitHubModelsProvider,
            "ollama": OllamaProvider,
        }
        provider_class = providers.get(provider_name)
        if provider_class is None:
            valid = ", ".join(sorted(providers))
            raise ValueError(f"Unsupported LLM provider '{provider_name}'. Valid providers: {valid}")
        return provider_class()
