from __future__ import annotations

import re
from typing import Literal

AuctionStatus = Literal["scheduled", "running", "closed", "canceled", "postponed", "redeemed", "unknown"]

_STATUS_PATTERNS: tuple[tuple[re.Pattern[str], AuctionStatus], ...] = (
    (re.compile(r"\b(redeemed|redeem)\b", re.IGNORECASE), "redeemed"),
    (re.compile(r"\b(cancelled|canceled|void)\b", re.IGNORECASE), "canceled"),
    (re.compile(r"\b(postponed|continued|rescheduled)\b", re.IGNORECASE), "postponed"),
    (re.compile(r"\b(running|active|in progress|open for bidding)\b", re.IGNORECASE), "running"),
    (re.compile(r"\b(closed|ended|sold|complete|completed)\b", re.IGNORECASE), "closed"),
    (re.compile(r"\b(scheduled|upcoming|pending|advertised)\b", re.IGNORECASE), "scheduled"),
)


def normalize_auction_status(value: str | None) -> AuctionStatus:
    if value is None:
        return "unknown"

    text = " ".join(value.strip().split())
    if not text:
        return "unknown"

    for pattern, status in _STATUS_PATTERNS:
        if pattern.search(text):
            return status

    return "unknown"
