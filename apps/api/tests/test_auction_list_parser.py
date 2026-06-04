from __future__ import annotations

from pathlib import Path

from app.parsing.auction_list_parser import parse_auction_list_html
from app.parsing.fixture_replay import replay_fixture

REPO_ROOT = Path(__file__).resolve().parents[3]
LIST_FIXTURE = REPO_ROOT / "fixtures/sarasota/html/realtaxdeed_auction_list.html"
DETAIL_FIXTURE = REPO_ROOT / "fixtures/sarasota/html/realtaxdeed_property_detail.html"


def test_parse_auction_list_html_returns_two_scheduled_and_redeemed_rows() -> None:
    html = LIST_FIXTURE.read_text(encoding="utf-8")
    records = parse_auction_list_html(html, fixture_path=LIST_FIXTURE)

    assert len(records) == 2
    scheduled, redeemed = records
    assert scheduled.case_number == "2026-TD-000456"
    assert scheduled.auction_status == "scheduled"
    assert scheduled.opening_bid_cents == 1_284_733
    assert scheduled.appraiser_assessment_cents == 19_850_000
    assert redeemed.case_number == "2026-TD-000457"
    assert redeemed.auction_status == "redeemed"
    assert redeemed.appraiser_assessment_cents == 0


def test_detail_fixture_uses_list_parser_only_when_rows_present() -> None:
    html = DETAIL_FIXTURE.read_text(encoding="utf-8")
    assert parse_auction_list_html(html, fixture_path=DETAIL_FIXTURE) == ()


def test_replay_fixture_list_matches_golden_expected() -> None:
    result = replay_fixture(LIST_FIXTURE)
    assert len(result.records) == 2
    assert result.quarantined_records == ()
