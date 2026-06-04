from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from app.parsing.auction_parser import (
    _canonical_field,
    _clean_optional,
    _extract_page_auction_date,
    normalize_auction_record,
)
from app.schemas.auction import NormalizedAuctionRecord

_LIST_TABLE_REQUIRED_HEADERS = frozenset({"case_number", "parcel_id", "opening_bid"})


class _TableCell:
    __slots__ = ("text", "href")

    def __init__(self) -> None:
        self.text = ""
        self.href: str | None = None


class _AuctionListTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[tuple[list[str], list[list[_TableCell]]]] = []
        self._in_table = False
        self._in_thead = False
        self._in_tbody = False
        self._in_row = False
        self._in_header_cell = False
        self._in_data_cell = False
        self._capture_anchor_href = False
        self._headers: list[str] = []
        self._rows: list[list[_TableCell]] = []
        self._current_row: list[_TableCell] | None = None
        self._current_cell: _TableCell | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "table":
            self._in_table = True
            self._headers = []
            self._rows = []
        elif self._in_table and lowered == "thead":
            self._in_thead = True
        elif self._in_table and lowered == "tbody":
            self._in_tbody = True
        elif self._in_table and lowered == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and lowered in {"th", "td"}:
            self._current_cell = _TableCell()
            self._in_header_cell = lowered == "th"
            self._in_data_cell = lowered == "td"
        elif self._in_data_cell and lowered == "a":
            for key, value in attrs:
                if key.lower() == "href" and value:
                    if self._current_cell is not None:
                        self._current_cell.href = value.strip()
                    self._capture_anchor_href = True

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "table" and self._in_table:
            if self._headers and self._rows:
                self.tables.append((self._headers, self._rows))
            self._in_table = False
            self._headers = []
            self._rows = []
        elif lowered == "thead":
            self._in_thead = False
        elif lowered == "tbody":
            self._in_tbody = False
        elif lowered == "tr" and self._in_row:
            if self._in_thead and self._current_row is not None:
                self._headers = [_normalize_cell_text(cell.text) for cell in self._current_row]
            elif self._in_tbody and self._current_row is not None and any(
                cell.text.strip() for cell in self._current_row
            ):
                self._rows.append(self._current_row)
            self._in_row = False
            self._current_row = None
        elif lowered in {"th", "td"}:
            if self._current_row is not None and self._current_cell is not None:
                self._current_cell.text = _normalize_cell_text(self._current_cell.text)
                self._current_row.append(self._current_cell)
            self._in_header_cell = False
            self._in_data_cell = False
            self._current_cell = None
            self._capture_anchor_href = False

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None and (self._in_header_cell or self._in_data_cell):
            self._current_cell.text += data


def parse_auction_list_html(
    html: str,
    *,
    fixture_path: str | Path | None = None,
) -> tuple[NormalizedAuctionRecord, ...]:
    parser = _AuctionListTableParser()
    parser.feed(html)
    page_auction_date = _extract_page_auction_date(html)

    for headers, rows in parser.tables:
        header_map = _header_field_map(headers)
        if not _LIST_TABLE_REQUIRED_HEADERS.issubset(header_map):
            continue

        records: list[NormalizedAuctionRecord] = []
        for row in rows:
            if len(row) < len(headers):
                continue
            extracted = _row_to_fields(row, header_map)
            if page_auction_date and "auction_date" not in extracted:
                extracted["auction_date"] = page_auction_date
            case_idx = header_map.get("case_number")
            if case_idx is not None and case_idx < len(row):
                href = row[case_idx].href
                if href:
                    extracted["detail_url"] = href
            records.append(
                normalize_auction_record(
                    extracted,
                    fixture_path=fixture_path,
                )
            )
        if records:
            return tuple(records)

    return ()


def _header_field_map(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, header in enumerate(headers):
        field = _canonical_field(header)
        if field is not None:
            mapping[field] = index
    return mapping


def _row_to_fields(row: list[_TableCell], header_map: dict[str, int]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for field, index in header_map.items():
        if index >= len(row):
            continue
        value = _clean_optional(row[index].text)
        if value is not None:
            fields[field] = value
    return fields


def _normalize_cell_text(value: str) -> str:
    return " ".join(unescape(value).split())
