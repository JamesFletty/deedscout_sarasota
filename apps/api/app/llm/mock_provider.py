import json

from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class MockProvider(LLMProvider):
    name = "mock"
    model_name = "deedscout-mock-v1"

    def complete(self, request: LLMRequest) -> LLMResponse:
        if len(request.prompt) > request.max_input_chars:
            raise ValueError("LLM request exceeds max_input_chars")
        if request.metadata.get("task") == "parcel_ambiguity_classifier":
            payload = {
                "classification": "ambiguous",
                "confidence": 0.55,
                "junk_reasons": [],
                "positive_reasons": ["mock provider keeps ambiguous records conservative"],
                "risk_flags": ["MOCK_CLASSIFIER"],
                "requires_human_review": True,
                "recommended_next_step": "manual_review",
            }
        else:
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
