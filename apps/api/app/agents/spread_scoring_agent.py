from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.agents.triage_types import Evidence, SpreadScore
from app.models.core import AuctionRecord


def score_spread(record: AuctionRecord) -> SpreadScore:
    opening_bid = record.opening_bid_cents
    assessment = record.appraiser_assessment_cents
    if assessment is None or assessment <= 0:
        return SpreadScore(
            None,
            None,
            (
                Evidence(
                    "spread.assessment_available",
                    "appraiser_assessment_cents",
                    assessment,
                    "manual_review",
                    "Assessment is missing or non-positive, so deterministic spread cannot be calculated.",
                ),
            ),
        )
    if opening_bid is None:
        return SpreadScore(
            None,
            None,
            (
                Evidence(
                    "spread.opening_bid_available",
                    "opening_bid_cents",
                    opening_bid,
                    "reject",
                    "Opening bid is missing, so deterministic spread cannot be calculated.",
                ),
            ),
        )

    estimated_spread = assessment - opening_bid
    ratio = (Decimal(opening_bid) / Decimal(assessment)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return SpreadScore(
        estimated_spread,
        ratio,
        (
            Evidence(
                "spread.estimated_spread",
                "appraiser_assessment_cents-opening_bid_cents",
                estimated_spread,
                "neutral",
                "Estimated spread is assessment minus opening bid for triage only, not valuation advice.",
            ),
            Evidence(
                "spread.opening_bid_ratio",
                "opening_bid_cents/appraiser_assessment_cents",
                str(ratio),
                "neutral",
                "Opening bid ratio is calculated only when assessment is positive.",
            ),
        ),
    )
