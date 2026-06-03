from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.llm.base import LLMRequest, LLMResponse
from app.llm.router import LLMRouter
from app.models import core  # noqa: F401
from app.models.core import AgentRun, AuctionBatch, AuctionRecord, CostEvent, TriageResult
from app.services.ambiguity_classifier_service import classify_ambiguous_records


class FakeRouter:
    def __init__(self, payloads: list[dict[str, Any] | str]) -> None:
        self.payloads = payloads
        self.calls_used = 0

    def complete_request(self, request: LLMRequest) -> LLMResponse:
        payload = self.payloads[self.calls_used]
        self.calls_used += 1
        if isinstance(payload, str):
            content = payload
            parsed_json = None
        else:
            content = json.dumps(payload, sort_keys=True)
            parsed_json = payload
        return LLMResponse(
            provider="fake",
            model_name="fake-model",
            content=content,
            parsed_json=parsed_json,
            input_tokens=10,
            output_tokens=5,
            estimated_cost_usd=0.01,
        )


@pytest.fixture
def session_factory():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def settings(max_calls: int = 5) -> Settings:
    return Settings(LLM_PROVIDER="mock", LLM_MAX_CALLS_PER_BATCH=max_calls, LLM_MAX_INPUT_CHARS=4000)


def seed_record_with_triage(
    session: Any,
    *,
    tier_1_status: str = "WATCHLIST",
    grade: str = "C",
    spread: int | None = 2_000_000,
    ratio: Decimal | None = Decimal("0.5000"),
    risk_flags: list[str] | None = None,
    batch: AuctionBatch | None = None,
) -> tuple[AuctionBatch, AuctionRecord, TriageResult]:
    if batch is None:
        batch = AuctionBatch(county="Sarasota", source="fixture", status="completed", started_at=core.utc_now())
        session.add(batch)
        session.flush()
    record = AuctionRecord(
        batch_id=batch.id,
        county="Sarasota",
        case_number="2026-TD-001",
        parcel_id_raw="0123-45-6789",
        parcel_id_normalized="0123456789",
        auction_status="scheduled",
        opening_bid_cents=5_000_000,
        appraiser_assessment_cents=20_000_000,
        parse_confidence=Decimal("0.9500"),
        missing_fields=[],
        parse_warnings=[],
    )
    session.add(record)
    session.flush()
    triage = TriageResult(
        auction_record_id=record.id,
        tier_1_status=tier_1_status,
        grade=grade,
        estimated_spread_cents=spread,
        opening_bid_ratio=ratio,
        data_quality_score=Decimal("0.9000"),
        risk_flags=risk_flags or ["ambiguous_junk:ROAD"],
        positive_signals=[],
        evidence=[
            {
                "rule_name": "test.ambiguous",
                "field_inspected": "property_text",
                "value": "ROAD TRACT",
                "decision_impact": "manual_review",
                "reason": "Ambiguous property text for testing.",
            }
        ],
        recommended_next_action="Watchlist for human review.",
        requires_human_review=True,
        llm_calls_used=0,
        estimated_cost_usd=Decimal("0"),
    )
    session.add(triage)
    session.commit()
    return batch, record, triage


def output_payload(classification: str, confidence: float, next_step: str) -> dict[str, Any]:
    return {
        "classification": classification,
        "confidence": confidence,
        "junk_reasons": ["test junk"] if classification == "likely_junk" else [],
        "positive_reasons": ["test positive"] if classification == "likely_investable" else [],
        "risk_flags": ["TEST_FLAG"],
        "requires_human_review": classification != "likely_junk",
        "recommended_next_step": next_step,
    }


def test_mock_provider_classifies_ambiguous_record(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, _ = seed_record_with_triage(session)
        summary = classify_ambiguous_records(session=session, batch_id=batch.id, settings=settings())
        run = session.scalar(select(AgentRun).where(AgentRun.batch_id == batch.id))
        cost = session.scalar(select(CostEvent).where(CostEvent.batch_id == batch.id))

    assert summary.attempted == 1
    assert run is not None
    assert cost is not None


def test_invalid_json_routes_to_manual_review(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, triage = seed_record_with_triage(session)
        classify_ambiguous_records(
            session=session,
            batch_id=batch.id,
            settings=settings(),
            router=FakeRouter(["not json"]),  # type: ignore[arg-type]
        )
        stored = session.get(TriageResult, triage.id)

    assert stored is not None
    assert stored.tier_1_status == "MANUAL_REVIEW"
    assert "LLM_OUTPUT_INVALID" in stored.risk_flags


def test_likely_junk_high_confidence_rejects(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, triage = seed_record_with_triage(session)
        router = FakeRouter([output_payload("likely_junk", 0.9, "reject")])
        classify_ambiguous_records(session=session, batch_id=batch.id, settings=settings(), router=router)  # type: ignore[arg-type]
        stored = session.get(TriageResult, triage.id)

    assert stored is not None
    assert stored.tier_1_status == "REJECTED"
    assert stored.grade == "F"


def test_likely_investable_promotes_only_if_spread_rules_pass(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, triage = seed_record_with_triage(session, spread=2_000_000, ratio=Decimal("0.5000"))
        router = FakeRouter([output_payload("likely_investable", 0.8, "research_candidate")])
        classify_ambiguous_records(session=session, batch_id=batch.id, settings=settings(), router=router)  # type: ignore[arg-type]
        stored = session.get(TriageResult, triage.id)

    assert stored is not None
    assert stored.tier_1_status == "RESEARCH_CANDIDATE"
    assert stored.grade == "B"

    with session_factory() as session:
        batch, _, triage = seed_record_with_triage(session, spread=2_000_000, ratio=Decimal("0.8000"))
        router = FakeRouter([output_payload("likely_investable", 0.8, "research_candidate")])
        classify_ambiguous_records(session=session, batch_id=batch.id, settings=settings(), router=router)  # type: ignore[arg-type]
        stored = session.get(TriageResult, triage.id)

    assert stored is not None
    assert stored.tier_1_status == "WATCHLIST"


def test_cost_cap_prevents_extra_calls(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, _ = seed_record_with_triage(session)
        seed_record_with_triage(session, batch=batch)
        router = FakeRouter([output_payload("ambiguous", 0.6, "manual_review")])
        summary = classify_ambiguous_records(
            session=session,
            batch_id=batch.id,
            settings=settings(max_calls=1),
            router=router,  # type: ignore[arg-type]
        )

    assert router.calls_used == 1
    assert summary.cost_cap_skipped == 1


def test_no_llm_call_for_deterministic_rejected_or_candidate_records(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, _ = seed_record_with_triage(session, tier_1_status="REJECTED", grade="F")
        seed_record_with_triage(session, tier_1_status="RESEARCH_CANDIDATE", grade="A", batch=batch)
        router = FakeRouter([])
        summary = classify_ambiguous_records(session=session, batch_id=batch.id, settings=settings(), router=router)  # type: ignore[arg-type]

    assert router.calls_used == 0
    assert summary.skipped == 2


def test_research_candidate_can_be_classified_when_forced(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch, _, _ = seed_record_with_triage(session, tier_1_status="RESEARCH_CANDIDATE", grade="A")
        router = FakeRouter([output_payload("ambiguous", 0.6, "manual_review")])
        summary = classify_ambiguous_records(
            session=session,
            batch_id=batch.id,
            settings=settings(),
            router=router,  # type: ignore[arg-type]
            force=True,
        )

    assert router.calls_used == 1
    assert summary.attempted == 1


def test_missing_provider_config_fails_clearly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_NAME"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="Azure OpenAI provider missing required configuration"):
        LLMRouter(Settings(LLM_PROVIDER="azure_openai"))
