from __future__ import annotations

from datetime import date, datetime


class DateParseError(ValueError):
    """Raised when a source date cannot be parsed without guessing."""


_DATE_FORMATS = ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y")


def parse_source_date(value: str) -> date:
    text = " ".join(value.strip().split())
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    raise DateParseError(f"Unparseable date value: {value!r}")
