from __future__ import annotations

import re
from dataclasses import dataclass


class ParcelParseError(ValueError):
    """Raised when a parcel value is blank or not usable as a source parcel ID."""


@dataclass(frozen=True)
class ParcelIdentifier:
    raw: str
    normalized: str


def normalize_parcel_id(value: str) -> ParcelIdentifier:
    raw = " ".join(value.strip().split())
    if not raw:
        raise ParcelParseError("Missing parcel ID; parser will not guess one")

    normalized = re.sub(r"[^0-9A-Za-z]", "", raw).upper()
    if not normalized:
        raise ParcelParseError(f"Parcel ID contains no searchable characters: {value!r}")

    return ParcelIdentifier(raw=raw, normalized=normalized)
