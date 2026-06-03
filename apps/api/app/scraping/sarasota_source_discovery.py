from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.scraping.playwright_client import PageClient, PageLoadResult

SourceStatus = Literal["reachable", "blocked", "changed", "failed"]


@dataclass(frozen=True)
class SourceDiscoveryResult:
    source_status: SourceStatus
    requested_url: str
    final_url: str | None
    http_status: int | None
    page_title: str | None
    notes: tuple[str, ...]
    page_result: PageLoadResult


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
