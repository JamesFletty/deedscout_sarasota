from __future__ import annotations

from pathlib import Path

import pytest

from app.parsing.fixture_replay import replay_fixture
from app.schemas.auction import FixtureReplayResult

REPO_ROOT = Path(__file__).resolve().parents[3]
HTML_DIR = REPO_ROOT / "fixtures/sarasota/html"
EXPECTED_DIR = REPO_ROOT / "fixtures/sarasota/expected"


@pytest.mark.parametrize(
    "fixture_name",
    [
        "sample_auction_detail.html",
        "realtaxdeed_property_detail.html",
        "realtaxdeed_auction_list.html",
        "clerk_tax_deed_auctions_landing.html",
    ],
)
def test_fixture_replay_matches_golden_expected(fixture_name: str) -> None:
    fixture_path = HTML_DIR / fixture_name
    expected_path = EXPECTED_DIR / f"{fixture_path.stem}.json"
    assert expected_path.is_file(), f"Missing golden file: {expected_path}"

    actual = replay_fixture(fixture_path)
    expected = FixtureReplayResult.model_validate_json(expected_path.read_text(encoding="utf-8"))
    assert actual.model_dump(mode="json") == expected.model_dump(mode="json")
