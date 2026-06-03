import pytest

from app.parsing.status_parser import normalize_auction_status


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Scheduled for auction", "scheduled"),
        ("Open for bidding", "running"),
        ("Sold / Closed", "closed"),
        ("Cancelled by clerk", "canceled"),
        ("Postponed", "postponed"),
        ("Redeemed", "redeemed"),
        ("unexpected source text", "unknown"),
        (None, "unknown"),
    ],
)
def test_normalize_auction_status_maps_visible_source_strings(source: str | None, expected: str) -> None:
    assert normalize_auction_status(source) == expected
