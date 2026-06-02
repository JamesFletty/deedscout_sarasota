import os

from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class GitHubModelsProvider(LLMProvider):
    name = "github_models"

    def __init__(self) -> None:
        missing = [key for key in ("GITHUB_TOKEN", "GITHUB_MODELS_MODEL") if not os.getenv(key)]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"GitHub Models provider missing required configuration: {joined}")
        self.endpoint = os.getenv("GITHUB_MODELS_ENDPOINT", "https://models.github.ai/inference")

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("GitHub Models network calls are not enabled in this MVP foundation")
