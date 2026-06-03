from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core import SourceSnapshot
from app.parsing.auction_parser import PARSER_VERSION
from app.storage.base import StorageBackend, StoredArtifact


@dataclass(frozen=True)
class SnapshotResult:
    snapshot: SourceSnapshot
    html_artifact: StoredArtifact | None
    screenshot_artifact: StoredArtifact | None


class _TagStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag.lower())


def snapshot_page(
    *,
    session: Session,
    storage: StorageBackend,
    batch_id: UUID,
    source_url: str,
    html: str,
    screenshot_bytes: bytes | None,
    auction_record_id: UUID | None = None,
    save_html: bool = True,
    save_screenshot: bool = True,
) -> SnapshotResult:
    html_artifact = storage.save_html(str(batch_id), source_url, html) if save_html else None
    screenshot_artifact = None
    if save_screenshot and screenshot_bytes is not None:
        screenshot_artifact = storage.save_screenshot(str(batch_id), source_url, screenshot_bytes)

    content_hash = (
        html_artifact.content_hash
        if html_artifact is not None
        else hashlib.sha256(html.encode("utf-8")).hexdigest()
    )
    snapshot = SourceSnapshot(
        auction_record_id=auction_record_id,
        batch_id=batch_id,
        source_url=source_url,
        html_path=html_artifact.uri if html_artifact is not None else None,
        screenshot_path=screenshot_artifact.uri if screenshot_artifact is not None else None,
        content_hash=content_hash,
        page_structure_hash=page_structure_hash(html),
        parser_version=PARSER_VERSION,
        scraped_at=datetime.now(UTC),
    )
    session.add(snapshot)
    session.flush()
    return SnapshotResult(snapshot=snapshot, html_artifact=html_artifact, screenshot_artifact=screenshot_artifact)


def page_structure_hash(html: str) -> str:
    parser = _TagStructureParser()
    parser.feed(html)
    structure = ">".join(parser.tags)
    return hashlib.sha256(structure.encode("utf-8")).hexdigest()
