import json

from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class MockProvider(LLMProvider):
    name = "mock"
    model_name = "deedscout-mock-v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if len(request.prompt) > request.max_input_chars:
            raise ValueError("LLM request exceeds max_input_chars")
        payload = {
            "decision": "manual_review",
            "confidence": 0.0,
            "reason": "deterministic mock provider for local validation",
        }
        content = json.dumps(payload, sort_keys=True)
        return LLMResponse(
            provider=self.name,
            model_name=self.model_name,
            content=content,
            parsed_json=payload if request.require_json else None,
            input_tokens=len(request.prompt.split()),
            output_tokens=len(content.split()),
        )
