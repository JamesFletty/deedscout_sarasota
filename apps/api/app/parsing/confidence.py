from __future__ import annotations


def clamp_confidence(score: float) -> float:
    return min(1.0, max(0.0, round(score, 4)))


def score_parse_confidence(
    *,
    case_number_present: bool,
    parcel_id_present: bool,
    opening_bid_parsed: bool,
    auction_status_parsed: bool,
    appraiser_assessment_parsed: bool,
    source_or_detail_url_present: bool,
) -> float:
    score = 0.0
    if case_number_present:
        score += 0.20
    if parcel_id_present:
        score += 0.20
    if opening_bid_parsed:
        score += 0.20
    if auction_status_parsed:
        score += 0.15
    if appraiser_assessment_parsed:
        score += 0.15
    if source_or_detail_url_present:
        score += 0.10
    return clamp_confidence(score)
