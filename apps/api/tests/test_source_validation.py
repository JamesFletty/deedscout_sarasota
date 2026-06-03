from __future__ import annotations

from pathlib import Path

import pytest

from app.parsing.fixture_replay import replay_fixture
from app.scraping.sarasota_sources import (
    SARASOTA_CLERK_TAX_DEED_AUCTIONS_URL,
    SARASOTA_REALTAXDEED_URL,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = REPO_ROOT / "fixtures/sarasota"
VALIDATION_DOC = FIXTURES / "SOURCE_VALIDATION.md"
CLERK_LANDING = FIXTURES / "html/clerk_tax_deed_auctions_landing.html"
REALTAXDEED_DETAIL = FIXTURES / "html/realtaxdeed_property_detail.html"


def test_source_validation_doc_exists_and_documents_primary_target() -> None:
    text = VALIDATION_DOC.read_text(encoding="utf-8")
    assert "realtaxdeed" in text.lower()
    assert "Option C" in text
    assert "403" in text


def test_canonical_source_urls_match_validation_doc() -> None:
    assert "sarasota.realtaxdeed.com" in SARASOTA_REALTAXDEED_URL
    assert "sarasotaclerk.com" in SARASOTA_CLERK_TAX_DEED_AUCTIONS_URL


def test_clerk_landing_fixture_has_no_parseable_auction_record() -> None:
    result = replay_fixture(CLERK_LANDING)
    assert result.records == ()
    assert len(result.quarantined_records) == 1


def test_realtaxdeed_detail_fixture_parses_core_fields() -> None:
    result = replay_fixture(REALTAXDEED_DETAIL)
    assert len(result.records) == 1
    record = result.records[0]
    assert record.case_number == "2026-TD-000456"
    assert record.parcel_id_normalized == "0145678901"
    assert record.opening_bid_cents == 1_284_733
    assert record.appraiser_assessment_cents == 19_850_000
    assert record.auction_status == "scheduled"
    assert record.parse_confidence >= 0.70


@pytest.mark.parametrize(
    "fixture_name",
    [
        "sample_auction_detail.html",
        "realtaxdeed_property_detail.html",
        "realtaxdeed_auction_list.html",
        "clerk_tax_deed_auctions_landing.html",
    ],
)
def test_committed_html_fixtures_exist(fixture_name: str) -> None:
    assert (FIXTURES / "html" / fixture_name).is_file()
