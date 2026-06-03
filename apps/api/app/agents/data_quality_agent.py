from __future__ import annotations

from decimal import Decimal

from app.agents.triage_types import DataQualityResult, Evidence
from app.models.core import AuctionRecord

LOW_PARSE_CONFIDENCE = Decimal("0.7000")


def evaluate_data_quality(record: AuctionRecord) -> DataQualityResult:
    score = Decimal("1.0000")
    missing: list[str] = []
    risk_flags: list[str] = []
    evidence: list[Evidence] = []

    checks = (
        (
            "parcel_id_normalized",
            record.parcel_id_normalized,
            Decimal("0.20"),
            "Missing parcel ID prevents parcel-level review.",
        ),
        ("case_number", record.case_number, Decimal("0.15"), "Missing case number weakens source traceability."),
        (
            "opening_bid_cents",
            record.opening_bid_cents,
            Decimal("0.20"),
            "Missing opening bid prevents spread screening.",
        ),
        (
            "appraiser_assessment_cents",
            record.appraiser_assessment_cents,
            Decimal("0.20"),
            "Missing appraiser assessment prevents deterministic value spread screening.",
        ),
    )
    for field_name, value, penalty, reason in checks:
        if value in (None, ""):
            score -= penalty
            missing.append(field_name)
            risk_flags.append(f"missing_{field_name}")
            evidence.append(Evidence("data_quality.required_field", field_name, value, "negative", reason))
        else:
            evidence.append(
                Evidence("data_quality.required_field", field_name, value, "neutral", f"{field_name} is present.")
            )

    parse_confidence = Decimal(record.parse_confidence)
    if parse_confidence < LOW_PARSE_CONFIDENCE:
        score -= Decimal("0.25")
        risk_flags.append("low_parse_confidence")
        evidence.append(
            Evidence(
                "data_quality.parse_confidence",
                "parse_confidence",
                str(parse_confidence),
                "quarantine",
                "Parse confidence is below the deterministic triage threshold.",
            )
        )
    else:
        evidence.append(
            Evidence(
                "data_quality.parse_confidence",
                "parse_confidence",
                str(parse_confidence),
                "neutral",
                "Parse confidence meets the deterministic triage threshold.",
            )
        )

    clamped = min(Decimal("1.0000"), max(Decimal("0.0000"), score)).quantize(Decimal("0.0001"))
    return DataQualityResult(clamped, tuple(missing), tuple(risk_flags), tuple(evidence))
