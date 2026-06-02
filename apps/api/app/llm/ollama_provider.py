import os

from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        missing = [key for key in ("OLLAMA_BASE_URL", "OLLAMA_MODEL") if not os.getenv(key)]
        if missing:
            raise ValueError(f"Ollama provider missing required configuration: {', '.join(missing)}")

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError("Ollama network calls are not enabled in this MVP foundation")
