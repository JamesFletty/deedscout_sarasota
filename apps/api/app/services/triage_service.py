from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.dedupe_agent import duplicate_evidence
from app.agents.final_triage_agent import triage_record
from app.models.core import AuctionBatch, AuctionRecord, TriageResult


class BatchNotFoundError(ValueError):
    """Raised when Tier 1 triage is requested for an unknown batch."""


def run_tier1_triage(session: Session, batch_id: UUID) -> list[TriageResult]:
    batch = session.get(AuctionBatch, batch_id)
    if batch is None:
        raise BatchNotFoundError(f"Auction batch not found: {batch_id}")

    records = list(session.scalars(select(AuctionRecord).where(AuctionRecord.batch_id == batch_id)).all())
    duplicate_map = duplicate_evidence(records)
    results: list[TriageResult] = []

    for record in records:
        extra_evidence = (duplicate_map[record.id],) if record.id in duplicate_map else ()
        decision = triage_record(record, extra_evidence=extra_evidence)
        triage_result = TriageResult(
            auction_record_id=record.id,
            tier_1_status=decision.tier_1_status,
            grade=decision.grade,
            estimated_spread_cents=decision.estimated_spread_cents,
            opening_bid_ratio=decision.opening_bid_ratio,
            data_quality_score=decision.data_quality_score,
            risk_flags=list(decision.risk_flags),
            positive_signals=list(decision.positive_signals),
            evidence=decision.evidence_json(),
            recommended_next_action=decision.recommended_next_action,
            requires_human_review=decision.requires_human_review,
            llm_calls_used=0,
            estimated_cost_usd=Decimal("0"),
        )
        session.add(triage_result)
        results.append(triage_result)

    _update_batch_counts(batch, results)
    session.commit()
    for result in results:
        session.refresh(result)
    return results


def _update_batch_counts(batch: AuctionBatch, results: list[TriageResult]) -> None:
    batch.records_rejected = sum(1 for result in results if result.tier_1_status == "REJECTED")
    batch.records_watchlist = sum(1 for result in results if result.tier_1_status == "WATCHLIST")
    batch.records_research_candidates = sum(
        1 for result in results if result.tier_1_status == "RESEARCH_CANDIDATE"
    )
    batch.records_manual_review = sum(1 for result in results if result.tier_1_status == "MANUAL_REVIEW")
    batch.records_quarantined = sum(1 for result in results if result.tier_1_status == "QUARANTINED")
    batch.llm_calls_used = 0
    batch.estimated_cost_usd = Decimal("0")
