from app.parsing.confidence import clamp_confidence, score_parse_confidence


def test_score_parse_confidence_uses_required_weights() -> None:
    score = score_parse_confidence(
        case_number_present=True,
        parcel_id_present=True,
        opening_bid_parsed=True,
        auction_status_parsed=True,
        appraiser_assessment_parsed=True,
        source_or_detail_url_present=True,
    )

    assert score == 1.0


def test_score_parse_confidence_does_not_add_missing_field_weight() -> None:
    score = score_parse_confidence(
        case_number_present=True,
        parcel_id_present=False,
        opening_bid_parsed=True,
        auction_status_parsed=False,
        appraiser_assessment_parsed=False,
        source_or_detail_url_present=True,
    )

    assert score == 0.5


def test_clamp_confidence_bounds_values() -> None:
    assert clamp_confidence(-0.2) == 0.0
    assert clamp_confidence(1.2) == 1.0
