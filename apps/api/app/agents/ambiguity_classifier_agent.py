from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.llm.base import LLMRequest, LLMResponse
from app.llm.router import LLMRouter
from app.models.core import AuctionRecord, TriageResult

Classification = Literal["likely_investable", "likely_junk", "ambiguous"]
RecommendedNextStep = Literal["reject", "watchlist", "research_candidate", "manual_review"]

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "parcel_ambiguity_classifier.txt"


class AmbiguityClassifierInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    county: str
    case_number: str | None
    parcel_id: str | None
    auction_status: str | None
    opening_bid_cents: int | None
    appraiser_assessment_cents: int | None
    estimated_spread_cents: int | None
    opening_bid_ratio: str | None
    legal_description_text: str | None
    property_address: str | None
    known_flags: list[str]
    deterministic_evidence: list[dict[str, object]]


class AmbiguityClassifierOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    classification: Classification
    confidence: float = Field(ge=0.0, le=1.0)
    junk_reasons: list[str] = Field(default_factory=list)
    positive_reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    requires_human_review: bool
    recommended_next_step: RecommendedNextStep


class AmbiguityClassifierResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_payload: AmbiguityClassifierInput
    output: AmbiguityClassifierOutput | None
    response: LLMResponse | None
    invalid_output: bool = False
    error_message: str | None = None


def should_classify_with_llm(triage_result: TriageResult, *, force: bool = False) -> bool:
    if force:
        return triage_result.tier_1_status in {"WATCHLIST", "MANUAL_REVIEW", "RESEARCH_CANDIDATE"}
    if triage_result.tier_1_status not in {"WATCHLIST", "MANUAL_REVIEW"}:
        return False
    flags = {str(flag) for flag in triage_result.risk_flags}
    if any(flag.startswith("ambiguous_junk:") for flag in flags):
        return True
    if "ambiguous_auction_status" in flags or "missing_or_invalid_assessment" in flags:
        return True
    evidence_text = json.dumps(triage_result.evidence).lower()
    return "property text" in evidence_text or "manual" in evidence_text or "ambiguous" in evidence_text


class AmbiguityClassifierAgent:
    def __init__(self, *, settings: Settings, router: LLMRouter | None = None) -> None:
        self.settings = settings
        self.router = router or LLMRouter(settings)
        self.system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    def classify(
        self,
        *,
        record: AuctionRecord,
        triage_result: TriageResult,
        legal_description_text: str | None = None,
        property_address: str | None = None,
    ) -> AmbiguityClassifierResult:
        payload = build_classifier_input(
            record=record,
            triage_result=triage_result,
            legal_description_text=legal_description_text,
            property_address=property_address,
        )
        prompt = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        if len(prompt) > self.settings.llm_max_input_chars:
            return AmbiguityClassifierResult(
                input_payload=payload,
                output=None,
                response=None,
                error_message="LLM_MAX_INPUT_CHARS exceeded before provider call",
            )

        request = LLMRequest(
            prompt=prompt,
            system_prompt=self.system_prompt,
            metadata={"task": "parcel_ambiguity_classifier", "timeout_seconds": self.settings.llm_timeout_seconds},
            require_json=True,
            max_input_chars=self.settings.llm_max_input_chars,
        )
        attempts = self.settings.llm_retry_count + 1
        last_error: str | None = None
        for _ in range(attempts):
            try:
                response = self.router.complete_request(request)
                parsed = response.parsed_json
                if parsed is None:
                    parsed = json.loads(response.content)
                output = AmbiguityClassifierOutput.model_validate(parsed)
                return AmbiguityClassifierResult(input_payload=payload, output=output, response=response)
            except (ValueError, json.JSONDecodeError, ValidationError) as exc:
                last_error = str(exc)
                if isinstance(exc, (json.JSONDecodeError, ValidationError)):
                    return AmbiguityClassifierResult(
                        input_payload=payload,
                        output=None,
                        response=response if "response" in locals() else None,
                        invalid_output=True,
                        error_message=last_error,
                    )
        return AmbiguityClassifierResult(input_payload=payload, output=None, response=None, error_message=last_error)


def build_classifier_input(
    *,
    record: AuctionRecord,
    triage_result: TriageResult,
    legal_description_text: str | None,
    property_address: str | None,
) -> AmbiguityClassifierInput:
    return AmbiguityClassifierInput(
        county=record.county,
        case_number=record.case_number,
        parcel_id=record.parcel_id_normalized or record.parcel_id_raw,
        auction_status=record.auction_status,
        opening_bid_cents=record.opening_bid_cents,
        appraiser_assessment_cents=record.appraiser_assessment_cents,
        estimated_spread_cents=triage_result.estimated_spread_cents,
        opening_bid_ratio=str(triage_result.opening_bid_ratio) if triage_result.opening_bid_ratio is not None else None,
        legal_description_text=legal_description_text,
        property_address=property_address,
        known_flags=[str(flag) for flag in triage_result.risk_flags],
        deterministic_evidence=[dict(item) for item in triage_result.evidence],
    )


def spread_rules_pass(triage_result: TriageResult) -> bool:
    if triage_result.estimated_spread_cents is None or triage_result.opening_bid_ratio is None:
        return False
    return (
        triage_result.estimated_spread_cents >= 1_500_000
        and Decimal(triage_result.opening_bid_ratio) <= Decimal("0.6500")
    )
