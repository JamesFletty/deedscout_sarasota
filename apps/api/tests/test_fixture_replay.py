from pathlib import Path

from app.parsing.fixture_replay import replay_fixture

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_FIXTURE = REPO_ROOT / "fixtures/sarasota/html/sample_auction_detail.html"


def test_fixture_replay_parses_sample_fixture() -> None:
    result = replay_fixture(SAMPLE_FIXTURE)

    assert len(result.records) == 1
    assert result.quarantined_records == ()
    record = result.records[0]
    assert record.case_number == "2026-TD-000123"
    assert record.parcel_id_raw == "0123-45-6789"
    assert record.parcel_id_normalized == "0123456789"
    assert record.opening_bid_cents == 842000
    assert record.appraiser_assessment_cents == 12500000
    assert record.auction_status == "scheduled"
    assert record.parse_confidence == 1.0
    assert record.missing_fields == ()


def test_low_confidence_record_routes_to_quarantine_style_output(tmp_path) -> None:  # type: ignore[no-untyped-def]
    fixture = tmp_path / "low_confidence.html"
    fixture.write_text(
        """
        <html><body>
          <p>Auction Status: Mystery review needed</p>
          <p>Opening Bid: not listed</p>
        </body></html>
        """,
        encoding="utf-8",
    )

    result = replay_fixture(fixture)

    assert result.records == ()
    assert len(result.quarantined_records) == 1
    quarantined = result.quarantined_records[0]
    assert quarantined.parse_confidence == 0.0
    assert "case_number" in quarantined.missing_fields
    assert "parcel_id" in quarantined.missing_fields
    assert "opening_bid" in quarantined.missing_fields
    assert "missing critical fields" in quarantined.quarantine_reason
