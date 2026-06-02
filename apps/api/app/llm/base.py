from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    require_json: bool = True
    max_input_chars: int = 4000


class LLMResponse(BaseModel):
    provider: str
    model_name: str
    content: str
    parsed_json: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse: ...
