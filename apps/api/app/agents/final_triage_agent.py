from __future__ import annotations

from decimal import Decimal

from app.agents.cost_gatekeeper_agent import deterministic_no_llm_evidence, llm_cost_usd
from app.agents.data_quality_agent import LOW_PARSE_CONFIDENCE, evaluate_data_quality
from app.agents.junk_filter_agent import evaluate_junk_signals
from app.agents.spread_scoring_agent import score_spread
from app.agents.triage_types import Evidence, SpreadScore, TriageDecision
from app.models.core import AuctionRecord

MIN_ACCEPTABLE_SPREAD_CENTS = 1_000_000
RESEARCH_SPREAD_CENTS = 1_500_000
HIGH_BID_RATIO = Decimal("0.9000")
RESEARCH_MAX_RATIO = Decimal("0.6500")
WATCHLIST_MAX_RATIO = Decimal("0.8000")
INACTIVE_STATUSES = {"canceled", "cancelled", "postponed", "redeemed", "closed", "inactive", "void"}
ACTIVE_STATUSES = {"scheduled", "running"}


def triage_record(
    record: AuctionRecord,
    *,
    property_text: str | None = None,
    extra_evidence: tuple[Evidence, ...] = (),
) -> TriageDecision:
    data_quality = evaluate_data_quality(record)
    spread = score_spread(record)
    junk = evaluate_junk_signals(property_text)
    evidence = [
        *data_quality.evidence,
        *spread.evidence,
        *junk.evidence,
        *extra_evidence,
        deterministic_no_llm_evidence(),
    ]
    risk_flags = [*data_quality.risk_flags, *junk.risk_flags]
    positive_signals: list[str] = []

    parse_confidence = Decimal(record.parse_confidence)
    status = (record.auction_status or "unknown").strip().lower()
    evidence.append(
        Evidence(
            "status.auction_status",
            "auction_status",
            record.auction_status,
            "neutral",
            "Auction status is evaluated before any candidate promotion.",
        )
    )

    if parse_confidence < LOW_PARSE_CONFIDENCE:
        return _decision(
            "QUARANTINED",
            "U",
            spread,
            data_quality.score,
            [*risk_flags, "parse_confidence_below_threshold"],
            positive_signals,
            evidence,
            "Quarantine for parser/source review before deterministic screening continues.",
            True,
        )

    if status in INACTIVE_STATUSES:
        grade = "F" if data_quality.score >= Decimal("0.7000") else "U"
        evidence.append(
            Evidence(
                "status.inactive",
                "auction_status",
                record.auction_status,
                "inactive",
                "Auction status indicates the record is canceled, postponed, redeemed, closed, or inactive-equivalent.",
            )
        )
        return _decision(
            "CANCELED_OR_INACTIVE",
            grade,
            spread,
            data_quality.score,
            [*risk_flags, "inactive_status"],
            positive_signals,
            evidence,
            "Do not promote inactive records; verify status manually only if needed for records research.",
            grade == "U",
        )

    if not record.parcel_id_normalized:
        evidence.append(
            Evidence(
                "hard_reject.missing_parcel",
                "parcel_id_normalized",
                record.parcel_id_normalized,
                "reject",
                "Missing parcel ID is a deterministic hard reject because parcel research cannot be anchored.",
            )
        )
        return _decision(
            "REJECTED",
            "F",
            spread,
            data_quality.score,
            [*risk_flags, "missing_parcel_id"],
            positive_signals,
            evidence,
            "Reject from Tier 1 until a parcel ID is available from source evidence.",
            False,
        )

    if record.opening_bid_cents is None or record.opening_bid_cents <= 0:
        evidence.append(
            Evidence(
                "hard_reject.invalid_opening_bid",
                "opening_bid_cents",
                record.opening_bid_cents,
                "reject",
                "Opening bid is missing, invalid, or non-positive.",
            )
        )
        return _decision(
            "REJECTED",
            "F",
            spread,
            data_quality.score,
            [*risk_flags, "invalid_opening_bid"],
            positive_signals,
            evidence,
            "Reject from Tier 1 until a valid positive opening bid is available.",
            False,
        )

    if junk.hard_reject:
        return _decision(
            "REJECTED",
            "F",
            spread,
            data_quality.score,
            [*risk_flags, "hard_junk_signal"],
            positive_signals,
            evidence,
            "Reject from Tier 1 due to deterministic junk parcel indicator; verify source text during human review.",
            False,
        )

    if status not in ACTIVE_STATUSES:
        evidence.append(
            Evidence(
                "status.ambiguous",
                "auction_status",
                record.auction_status,
                "manual_review",
                "Auction status is not an active status that can be safely promoted by deterministic rules.",
            )
        )
        return _decision(
            "MANUAL_REVIEW",
            "U",
            spread,
            data_quality.score,
            [*risk_flags, "ambiguous_auction_status"],
            positive_signals,
            evidence,
            "Manually verify auction status before screening this record further.",
            True,
        )

    if record.appraiser_assessment_cents is None or record.appraiser_assessment_cents <= 0:
        return _decision(
            "MANUAL_REVIEW",
            "U",
            spread,
            data_quality.score,
            [*risk_flags, "missing_or_invalid_assessment"],
            positive_signals,
            evidence,
            "Manually look up assessment before making any Tier 1 spread classification.",
            True,
        )

    if spread.opening_bid_ratio is None or spread.estimated_spread_cents is None:
        return _decision(
            "MANUAL_REVIEW",
            "U",
            spread,
            data_quality.score,
            [*risk_flags, "spread_not_calculated"],
            positive_signals,
            evidence,
            "Manual review required because spread metrics could not be calculated safely.",
            True,
        )

    if spread.opening_bid_ratio >= HIGH_BID_RATIO:
        evidence.append(
            Evidence(
                "hard_reject.high_bid_ratio",
                "opening_bid_ratio",
                str(spread.opening_bid_ratio),
                "reject",
                "Opening bid is at least 90% of appraiser assessment, failing Tier 1 spread screening.",
            )
        )
        return _decision(
            "REJECTED",
            "F",
            spread,
            data_quality.score,
            [*risk_flags, "high_opening_bid_ratio"],
            positive_signals,
            evidence,
            "Reject from Tier 1 due to weak assessment-to-opening-bid spread.",
            False,
        )


    if spread.estimated_spread_cents < MIN_ACCEPTABLE_SPREAD_CENTS:
        evidence.append(
            Evidence(
                "hard_reject.low_spread",
                "estimated_spread_cents",
                spread.estimated_spread_cents,
                "reject",
                "Estimated spread is below the $10,000 Tier 1 minimum.",
            )
        )
        return _decision(
            "REJECTED",
            "F",
            spread,
            data_quality.score,
            [*risk_flags, "low_estimated_spread"],
            positive_signals,
            evidence,
            "Reject from Tier 1 due to low deterministic spread.",
            False,
        )


    if spread.opening_bid_ratio <= RESEARCH_MAX_RATIO:
        positive_signals.append("opening_bid_ratio_at_or_below_65_percent")
    if spread.estimated_spread_cents >= RESEARCH_SPREAD_CENTS:
        positive_signals.append("estimated_spread_at_or_above_15000")

    if (
        spread.opening_bid_ratio <= RESEARCH_MAX_RATIO
        and spread.estimated_spread_cents >= RESEARCH_SPREAD_CENTS
        and data_quality.score >= Decimal("0.7000")
        and not junk.ambiguous
        and not extra_evidence
    ):
        return _decision(
            "RESEARCH_CANDIDATE",
            "A",
            spread,
            data_quality.score,
            risk_flags,
            positive_signals,
            evidence,
            "Research candidate for qualified human due-diligence review; this is not bidding, title, or value advice.",
            False,
        )

    if (
        junk.ambiguous
        or spread.opening_bid_ratio <= WATCHLIST_MAX_RATIO
        or spread.estimated_spread_cents >= MIN_ACCEPTABLE_SPREAD_CENTS
    ):
        return _decision(
            "WATCHLIST",
            "C",
            spread,
            data_quality.score,
            risk_flags,
            positive_signals,
            evidence,
            "Watchlist for human review because deterministic signals are mixed or unresolved.",
            True,
        )

    return _decision(
        "MANUAL_REVIEW",
        "U",
        spread,
        data_quality.score,
        [*risk_flags, "unresolved_deterministic_classification"],
        positive_signals,
        evidence,
        "Manual review required because deterministic rules did not safely classify the record.",
        True,
    )


def _decision(
    status: str,
    grade: str,
    spread: SpreadScore,
    data_quality_score: Decimal,
    risk_flags: list[str],
    positive_signals: list[str],
    evidence: list[Evidence],
    next_action: str,
    requires_human_review: bool,
) -> TriageDecision:
    return TriageDecision(
        tier_1_status=status,  # type: ignore[arg-type]
        grade=grade,  # type: ignore[arg-type]
        estimated_spread_cents=spread.estimated_spread_cents,
        opening_bid_ratio=spread.opening_bid_ratio,
        data_quality_score=data_quality_score,
        risk_flags=tuple(dict.fromkeys(risk_flags)),
        positive_signals=tuple(dict.fromkeys(positive_signals)),
        evidence=tuple(evidence),
        recommended_next_action=next_action,
        requires_human_review=requires_human_review,
        llm_calls_used=0,
        estimated_cost_usd=llm_cost_usd(),
    )
