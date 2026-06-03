from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_MONEY_PATTERN = re.compile(r"^\$?\s*(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?)$")


class MoneyParseError(ValueError):
    """Raised when a source money value cannot be parsed without guessing."""


def parse_money_to_cents(value: str) -> int:
    text = value.strip()
    match = _MONEY_PATTERN.fullmatch(text)
    if match is None:
        raise MoneyParseError(f"Unparseable money value: {value!r}")

    amount_text = match.group("amount").replace(",", "")
    try:
        amount = Decimal(amount_text)
    except InvalidOperation as exc:
        raise MoneyParseError(f"Unparseable money value: {value!r}") from exc

    cents = (amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(cents)
