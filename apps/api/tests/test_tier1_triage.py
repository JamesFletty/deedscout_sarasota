from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.agents.final_triage_agent import triage_record
from app.db.base import Base
from app.models import core  # noqa: F401
from app.models.core import AuctionBatch, AuctionRecord, TriageResult
from app.services.triage_service import run_tier1_triage


@pytest.fixture
def session_factory():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def make_record(**overrides: object) -> AuctionRecord:
    values = {
        "batch_id": overrides.pop("batch_id", None),
        "county": "Sarasota",
        "case_number": "2026-TD-001",
        "parcel_id_raw": "0123-45-6789",
        "parcel_id_normalized": "0123456789",
        "auction_status": "scheduled",
        "opening_bid_cents": 5_000_000,
        "appraiser_assessment_cents": 20_000_000,
        "detail_url": "https://example.test/detail",
        "parse_confidence": Decimal("0.9500"),
        "missing_fields": [],
        "parse_warnings": [],
    }
    values.update(overrides)
    return AuctionRecord(**values)


def test_canceled_record_routes_to_canceled_or_inactive() -> None:
    decision = triage_record(make_record(auction_status="canceled"))

    assert decision.tier_1_status == "CANCELED_OR_INACTIVE"
    assert decision.grade == "F"


def test_low_confidence_routes_to_quarantined() -> None:
    decision = triage_record(make_record(parse_confidence=Decimal("0.6900")))

    assert decision.tier_1_status == "QUARANTINED"
    assert decision.grade == "U"


def test_missing_parcel_rejects() -> None:
    decision = triage_record(make_record(parcel_id_normalized=None, parcel_id_raw=None))

    assert decision.tier_1_status == "REJECTED"
    assert "missing_parcel_id" in decision.risk_flags


def test_missing_assessment_routes_to_manual_review() -> None:
    decision = triage_record(make_record(appraiser_assessment_cents=None))

    assert decision.tier_1_status == "MANUAL_REVIEW"
    assert decision.grade == "U"


def test_high_bid_ratio_rejects() -> None:
    decision = triage_record(make_record(opening_bid_cents=9_500_000, appraiser_assessment_cents=10_000_000))

    assert decision.tier_1_status == "REJECTED"
    assert "high_opening_bid_ratio" in decision.risk_flags


def test_low_spread_rejects() -> None:
    decision = triage_record(make_record(opening_bid_cents=100_000, appraiser_assessment_cents=1_000_000))

    assert decision.tier_1_status == "REJECTED"
    assert "low_estimated_spread" in decision.risk_flags


def test_hard_junk_legal_text_rejects() -> None:
    decision = triage_record(make_record(), property_text="Retention pond tract for stormwater")

    assert decision.tier_1_status == "REJECTED"
    assert "hard_junk_signal" in decision.risk_flags


def test_tract_only_ambiguous_text_does_not_hard_reject() -> None:
    decision = triage_record(make_record(opening_bid_cents=12_000_000), property_text="TRACT 12 GREEN SUBDIVISION")

    assert decision.tier_1_status != "REJECTED"
    assert "hard_junk_signal" not in decision.risk_flags


def test_strong_spread_candidate_becomes_research_candidate() -> None:
    decision = triage_record(make_record(opening_bid_cents=5_000_000, appraiser_assessment_cents=25_000_000))

    assert decision.tier_1_status == "RESEARCH_CANDIDATE"
    assert decision.grade == "A"


def test_every_result_contains_evidence_and_no_llm_provider_is_called(session_factory) -> None:  # type: ignore[no-untyped-def]
    with session_factory() as session:
        batch = AuctionBatch(county="Sarasota", source="fixture", status="completed", started_at=core.utc_now())
        session.add(batch)
        session.flush()
        session.add(make_record(batch_id=batch.id))
        session.commit()

        results = run_tier1_triage(session, batch.id)
        stored = session.scalar(
            select(TriageResult).where(TriageResult.auction_record_id == results[0].auction_record_id)
        )

    assert stored is not None
    assert stored.evidence
    required_evidence_keys = {"rule_name", "field_inspected", "value", "decision_impact", "reason"}
    assert all(required_evidence_keys <= set(item) for item in stored.evidence)
    assert stored.llm_calls_used == 0
    assert stored.estimated_cost_usd == Decimal("0.0000")
