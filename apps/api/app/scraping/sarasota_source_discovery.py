from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urljoin

from app.scraping.playwright_client import PageClient, PageLoadResult

SourceStatus = Literal["reachable", "blocked", "changed", "failed"]

RECORD_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "case_number": re.compile(r"\bcase\s*(number|no\.?|#)\b", re.IGNORECASE),
    "parcel_id": re.compile(r"\b(parcel\s+(id|number)|alternate\s+key)\b", re.IGNORECASE),
    "opening_bid": re.compile(r"\b(opening|minimum|starting)\s+bid\b", re.IGNORECASE),
    "auction_date": re.compile(r"\b((auction|sale)\s+date|auction\s+starts)\b", re.IGNORECASE),
    "auction_status": re.compile(
        r"\bauction\s+status\s*[:#-]?\s+(scheduled|running|closed|canceled|cancelled|postponed|redeemed|unknown)\b",
        re.IGNORECASE,
    ),
    "appraiser_assessment": re.compile(
        r"\b(appraiser\s+assessment|assessed\s+value|just\s+value|assessment)\b",
        re.IGNORECASE,
    ),
}


@dataclass(frozen=True)
class SourceLink:
    text: str
    href: str


@dataclass(frozen=True)
class SarasotaSourceStructure:
    source_url: str
    page_title: str | None
    record_field_presence: dict[str, bool]
    auction_calendar_url: str | None
    property_appraiser_url: str | None
    assessment_values_present: bool
    notes: tuple[str, ...]


@dataclass(frozen=True)
class SourceDiscoveryResult:
    source_status: SourceStatus
    requested_url: str
    final_url: str | None
    http_status: int | None
    page_title: str | None
    notes: tuple[str, ...]
    page_result: PageLoadResult


class _SourceStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.visible_parts: list[str] = []
        self.links: list[SourceLink] = []
        self.title_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._current_href: str | None = None
        self._current_link_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if normalized_tag == "title":
            self._in_title = True
        if normalized_tag == "a":
            self._current_href = _attr_value(attrs, "href")
            self._current_link_parts = []

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if normalized_tag == "title":
            self._in_title = False
        if normalized_tag == "a" and self._current_href:
            link_text = _normalize_text(" ".join(self._current_link_parts))
            if link_text:
                self.links.append(SourceLink(text=link_text, href=self._current_href))
            self._current_href = None
            self._current_link_parts = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._current_href is not None:
            self._current_link_parts.append(data)
        self.visible_parts.append(data)

    @property
    def visible_text(self) -> str:
        return _normalize_text(" ".join(self.visible_parts))

    @property
    def page_title(self) -> str | None:
        title = _normalize_text(" ".join(self.title_parts))
        return title or None


def discover_sarasota_source(starting_url: str, client: PageClient) -> SourceDiscoveryResult:
    page = client.load_page(starting_url)
    notes: list[str] = []
    if page.error_message:
        notes.append(page.error_message)
    if page.blocked_reason:
        notes.append(page.blocked_reason)

    if page.status == "failed":
        status: SourceStatus = "failed"
    elif page.status == "blocked":
        status = "blocked"
    elif not page.html:
        status = "changed"
        notes.append("Page loaded but no HTML was returned for snapshotting")
    else:
        status = "reachable"

    return SourceDiscoveryResult(
        source_status=status,
        requested_url=starting_url,
        final_url=page.final_url,
        http_status=page.http_status,
        page_title=page.page_title,
        notes=tuple(notes),
        page_result=page,
    )


def analyze_sarasota_clerk_source(html: str, *, source_url: str) -> SarasotaSourceStructure:
    parser = _SourceStructureParser()
    parser.feed(html)
    visible_text = parser.visible_text
    field_presence = {
        field_name: pattern.search(visible_text) is not None
        for field_name, pattern in RECORD_FIELD_PATTERNS.items()
    }
    auction_calendar_url = _first_link_url_containing(parser.links, "Tax Deed Auction Calendar", source_url)
    property_appraiser_url = _first_link_url_containing(parser.links, "Property Appraiser", source_url)
    notes: list[str] = []

    if auction_calendar_url:
        notes.append("Clerk page links to an external RealTaxDeed auction calendar for current sale records.")
    else:
        notes.append("No auction calendar link was found on the captured Clerk page.")

    record_fields = ("case_number", "parcel_id", "opening_bid", "auction_date", "auction_status")
    if not any(field_presence[field] for field in record_fields):
        notes.append("Captured Clerk page is an informational landing page, not a parcel-level auction list.")
    if not field_presence["appraiser_assessment"]:
        notes.append("Property Appraiser assessment values are not present as parcel-level fields on the Clerk page.")
    if property_appraiser_url:
        notes.append("Clerk page provides a Property Appraiser resource link for manual cross-reference.")

    return SarasotaSourceStructure(
        source_url=source_url,
        page_title=parser.page_title,
        record_field_presence=field_presence,
        auction_calendar_url=auction_calendar_url,
        property_appraiser_url=property_appraiser_url,
        assessment_values_present=field_presence["appraiser_assessment"],
        notes=tuple(notes),
    )


def _attr_value(attrs: list[tuple[str, str | None]], name: str) -> str | None:
    for key, value in attrs:
        if key.lower() == name and value:
            return value.strip()
    return None


def _first_link_url_containing(links: list[SourceLink], text: str, source_url: str) -> str | None:
    expected = text.casefold()
    for link in links:
        if expected in link.text.casefold():
            return urljoin(source_url, link.href)
    return None


def _normalize_text(value: str) -> str:
    return " ".join(value.split())
