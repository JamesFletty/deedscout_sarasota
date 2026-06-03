from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from app.parsing.confidence import score_parse_confidence
from app.parsing.date_parser import DateParseError, parse_source_date
from app.parsing.money_parser import MoneyParseError, parse_money_to_cents
from app.parsing.parcel_parser import ParcelParseError, normalize_parcel_id
from app.parsing.status_parser import normalize_auction_status
from app.schemas.auction import NormalizedAuctionRecord

PARSER_VERSION = "sarasota-fixture-parser-v1"

_BLOCK_TAGS = {
    "address",
    "article",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "h1",
    "h2",
    "h3",
    "li",
    "p",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "case_number": ("case number", "case no", "case #", "tax deed case", "tax deed file", "tax deed file #"),
    "parcel_id": ("parcel id", "parcel number", "parcel", "property id", "alternate key"),
    "auction_date": ("auction date", "sale date", "auction starts"),
    "auction_status": ("auction status", "status"),
    "opening_bid": ("opening bid", "minimum bid", "starting bid"),
    "appraiser_assessment": ("appraiser assessment", "assessed value", "just value", "assessment"),
    "detail_url": ("detail url", "source url"),
    "notice_url": ("notice url", "notice"),
    "tax_deed_record_url": ("tax deed record url", "tax deed record"),
}


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")
        if tag.lower() == "a":
            for key, value in attrs:
                if key.lower() == "href" and value:
                    self.links.append(value.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return unescape("".join(self.parts))


def parse_auction_html(html: str, *, fixture_path: str | Path | None = None) -> NormalizedAuctionRecord:
    extracted = _extract_fields(html)
    warnings: list[str] = []
    missing: list[str] = []

    case_number = _clean_optional(extracted.get("case_number"))
    if case_number is None:
        missing.append("case_number")

    parcel_id_raw: str | None = None
    parcel_id_normalized: str | None = None
    parcel_source = _clean_optional(extracted.get("parcel_id"))
    if parcel_source is None:
        missing.append("parcel_id")
    else:
        try:
            parcel = normalize_parcel_id(parcel_source)
            parcel_id_raw = parcel.raw
            parcel_id_normalized = parcel.normalized
        except ParcelParseError as exc:
            warnings.append(str(exc))
            missing.append("parcel_id")

    auction_date = None
    auction_date_source = _clean_optional(extracted.get("auction_date"))
    if auction_date_source is None:
        missing.append("auction_date")
    else:
        try:
            auction_date = parse_source_date(auction_date_source)
        except DateParseError as exc:
            warnings.append(str(exc))
            missing.append("auction_date")

    auction_status_source = _clean_optional(extracted.get("auction_status"))
    auction_status = normalize_auction_status(auction_status_source)
    if auction_status_source is None:
        missing.append("auction_status")
    elif auction_status == "unknown":
        warnings.append(f"Unmapped auction status: {auction_status_source!r}")

    opening_bid_cents = _parse_optional_money(extracted.get("opening_bid"), "opening_bid", missing, warnings)
    appraiser_assessment_cents = _parse_optional_money(
        extracted.get("appraiser_assessment"), "appraiser_assessment", missing, warnings
    )

    detail_url = _clean_optional(extracted.get("detail_url")) or _first_link(html)
    notice_url = _clean_optional(extracted.get("notice_url"))
    tax_deed_record_url = _clean_optional(extracted.get("tax_deed_record_url"))

    confidence = score_parse_confidence(
        case_number_present=case_number is not None,
        parcel_id_present=parcel_id_normalized is not None,
        opening_bid_parsed=opening_bid_cents is not None,
        auction_status_parsed=auction_status_source is not None and auction_status != "unknown",
        appraiser_assessment_parsed=appraiser_assessment_cents is not None,
        source_or_detail_url_present=detail_url is not None,
    )

    return NormalizedAuctionRecord(
        case_number=case_number,
        parcel_id_raw=parcel_id_raw,
        parcel_id_normalized=parcel_id_normalized,
        auction_date=auction_date,
        auction_status=auction_status,
        opening_bid_cents=opening_bid_cents,
        appraiser_assessment_cents=appraiser_assessment_cents,
        detail_url=detail_url,
        notice_url=notice_url,
        tax_deed_record_url=tax_deed_record_url,
        source_fixture_path=str(fixture_path) if fixture_path is not None else None,
        parse_confidence=confidence,
        missing_fields=tuple(dict.fromkeys(missing)),
        parse_warnings=tuple(warnings),
    )


def _parse_optional_money(value: str | None, field_name: str, missing: list[str], warnings: list[str]) -> int | None:
    source = _clean_optional(value)
    if source is None:
        missing.append(field_name)
        return None
    try:
        return parse_money_to_cents(source)
    except MoneyParseError as exc:
        warnings.append(str(exc))
        missing.append(field_name)
        return None


def _extract_fields(html: str) -> dict[str, str]:
    parser = _VisibleTextParser()
    parser.feed(html)
    lines = [_normalize_line(line) for line in parser.text().splitlines()]
    lines = [line for line in lines if line]
    fields: dict[str, str] = {}

    for line in lines:
        label, value = _split_inline_label(line)
        if label is not None and value is not None:
            _store_field(fields, label, value)

    for index, line in enumerate(lines[:-1]):
        if _canonical_field(line) is not None:
            _store_field(fields, line, lines[index + 1])

    return fields


def _split_inline_label(line: str) -> tuple[str | None, str | None]:
    if ":" not in line:
        return None, None
    label, value = line.split(":", 1)
    if not label.strip() or not value.strip():
        return None, None
    return label, value


def _store_field(fields: dict[str, str], label: str, value: str) -> None:
    canonical = _canonical_field(label)
    if canonical is not None and canonical not in fields:
        cleaned = _clean_optional(value)
        if cleaned is not None:
            fields[canonical] = cleaned


def _canonical_field(label: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9# ]", "", label.lower()).strip()
    normalized = " ".join(normalized.split())
    for field, aliases in _FIELD_ALIASES.items():
        if normalized in aliases:
            return field
    return None


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _normalize_line(value: str) -> str:
    return " ".join(value.strip().split())


def _first_link(html: str) -> str | None:
    parser = _VisibleTextParser()
    parser.feed(html)
    return next((link for link in parser.links if link), None)
