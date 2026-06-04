from __future__ import annotations

import json
from pathlib import Path

from app.parsing.auction_parser import parse_auction_documents
from app.schemas.auction import FixtureReplayResult, NormalizedAuctionRecord, QuarantinedAuctionRecord

LOW_CONFIDENCE_THRESHOLD = 0.70


def replay_fixture(path: str | Path) -> FixtureReplayResult:
    fixture_path = Path(path)
    html = fixture_path.read_text(encoding="utf-8")
    records: list[NormalizedAuctionRecord] = []
    quarantined: list[QuarantinedAuctionRecord] = []
    for record in parse_auction_documents(html, fixture_path=fixture_path):
        quarantine = _quarantine_if_needed(record)
        if quarantine is not None:
            quarantined.append(quarantine)
        else:
            records.append(record)
    return FixtureReplayResult(records=tuple(records), quarantined_records=tuple(quarantined))


def replay_fixtures(path: str | Path) -> FixtureReplayResult:
    fixture_dir = Path(path)
    records: list[NormalizedAuctionRecord] = []
    quarantined: list[QuarantinedAuctionRecord] = []
    for fixture_path in sorted(fixture_dir.glob("*.html")):
        result = replay_fixture(fixture_path)
        records.extend(result.records)
        quarantined.extend(result.quarantined_records)
    return FixtureReplayResult(records=tuple(records), quarantined_records=tuple(quarantined))


def write_expected_snapshot(result: FixtureReplayResult, fixture_path: str | Path, *, expected_dir: str | Path) -> Path:
    expected_root = Path(expected_dir)
    expected_root.mkdir(parents=True, exist_ok=True)
    source = Path(fixture_path)
    output_path = expected_root / f"{source.stem}.json"
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _quarantine_if_needed(record: NormalizedAuctionRecord) -> QuarantinedAuctionRecord | None:
    critical_missing = {"case_number", "parcel_id", "opening_bid"}.intersection(record.missing_fields)
    if record.parse_confidence >= LOW_CONFIDENCE_THRESHOLD and not critical_missing:
        return None

    reasons: list[str] = []
    if record.parse_confidence < LOW_CONFIDENCE_THRESHOLD:
        reasons.append(f"parse confidence {record.parse_confidence:.2f} below {LOW_CONFIDENCE_THRESHOLD:.2f}")
    if critical_missing:
        reasons.append("missing critical fields: " + ", ".join(sorted(critical_missing)))

    return QuarantinedAuctionRecord(
        source_fixture_path=record.source_fixture_path or "",
        parse_confidence=record.parse_confidence,
        missing_fields=record.missing_fields,
        parse_warnings=record.parse_warnings,
        extracted_record=record,
        quarantine_reason="; ".join(reasons),
    )
