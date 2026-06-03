import pytest

from app.parsing.money_parser import MoneyParseError, parse_money_to_cents


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("$8,420.00", 842000),
        ("8420", 842000),
        ("$ 8,420", 842000),
        ("8,420.50", 842050),
    ],
)
def test_parse_money_to_cents_accepts_sarasota_formats(source: str, expected: int) -> None:
    assert parse_money_to_cents(source) == expected


def test_parse_money_to_cents_fails_explicitly() -> None:
    with pytest.raises(MoneyParseError, match="Unparseable money value"):
        parse_money_to_cents("not listed")
