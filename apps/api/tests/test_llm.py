import pytest

from app.core.config import Settings
from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.base import LLMRequest
from app.llm.mock_provider import MockProvider
from app.llm.router import LLMRouter


def test_mock_provider_returns_deterministic_json() -> None:
    provider = MockProvider()

    first = provider.complete(LLMRequest(prompt="review record"))
    second = provider.complete(LLMRequest(prompt="review record"))

    assert first.content == second.content
    assert first.parsed_json == {
        "decision": "manual_review",
        "confidence": 0.0,
        "reason": "deterministic mock provider for local validation",
    }


def test_router_selects_mock_provider() -> None:
    router = LLMRouter(Settings(LLM_PROVIDER="mock"))

    response = router.complete("review record")

    assert response.provider == "mock"
    assert router.calls_used == 1


def test_router_rejects_invalid_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMRouter(Settings(LLM_PROVIDER="invalid"))


def test_external_provider_missing_credentials_fail_clearly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="Azure OpenAI provider missing required configuration"):
        AzureOpenAIProvider()
