from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import core  # noqa: F401
from app.models.core import AuctionBatch, AuctionRecord, ScraperFailure, SourceSnapshot
from app.scraping.playwright_client import (
    PageLoadResult,
    PlaywrightPageClient,
    RetryablePageLoadError,
    ScraperConfig,
    detect_blocked_reason,
)
from app.scraping.sarasota_auction_scraper import SarasotaAuctionScraper
from app.scraping.snapshotter import snapshot_page
from app.storage.local_storage import LocalStorage

SAMPLE_HTML = """
<html><head><title>Fixture</title></head><body>
<p>Case Number: 2026-TD-000123</p>
<p>Parcel ID: 0123-45-6789</p>
<p>Auction Date: 07/10/2026</p>
<p>Auction Status: Scheduled</p>
<p>Opening Bid: $8,420.00</p>
<p>Appraiser Assessment: $125,000</p>
<p>Detail URL: https://example.test/detail</p>
</body></html>
"""


@dataclass
class FakePageClient:
    result: PageLoadResult
    calls: int = 0

    def load_page(self, url: str) -> PageLoadResult:
        self.calls += 1
        return self.result


class AlwaysFailingPlaywrightClient(PlaywrightPageClient):
    def __init__(self, config: ScraperConfig) -> None:
        super().__init__(config)
        self.calls = 0

    def _load_once(self, url: str, *, attempt: int) -> PageLoadResult:
        self.calls += 1
        raise RetryablePageLoadError(f"attempt {attempt} failed")


@pytest.fixture
def session_factory():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def test_playwright_client_retry_settings_are_honored() -> None:
    client = AlwaysFailingPlaywrightClient(ScraperConfig(max_retries=2, delay_between_pages_ms=0))

    result = client.load_page("https://example.test/source")

    assert client.calls == 3
    assert result.status == "failed"
    assert result.attempts == 3
    assert result.error_message == "attempt 3 failed"


def test_scraper_config_rejects_invalid_max_pages() -> None:
    with pytest.raises(ValueError, match="max_pages"):
        ScraperConfig(max_pages=0)


def test_snapshotter_saves_html_screenshot_and_source_snapshot(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    storage = LocalStorage(tmp_path)
    with session_factory() as session:
        batch = AuctionBatch(county="Sarasota", source="fixture", status="running", started_at=core.utc_now())
        session.add(batch)
        session.flush()

        result = snapshot_page(
            session=session,
            storage=storage,
            batch_id=batch.id,
            source_url="https://example.test/detail",
            html=SAMPLE_HTML,
            screenshot_bytes=b"png-bytes",
        )

        stored = session.scalar(select(SourceSnapshot).where(SourceSnapshot.id == result.snapshot.id))

    assert result.html_artifact is not None
    assert result.screenshot_artifact is not None
    assert Path(result.html_artifact.uri).read_text(encoding="utf-8") == SAMPLE_HTML
    assert Path(result.screenshot_artifact.uri).read_bytes() == b"png-bytes"
    assert stored is not None
    assert stored.html_path == result.html_artifact.uri
    assert stored.screenshot_path == result.screenshot_artifact.uri
    assert stored.content_hash == result.html_artifact.content_hash


def test_scraper_creates_batch_stores_snapshot_and_parsed_record(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    client = FakePageClient(
        PageLoadResult(
            requested_url="https://example.test/source",
            final_url="https://example.test/source",
            status="success",
            http_status=200,
            page_title="Fixture",
            html=SAMPLE_HTML,
            screenshot_bytes=b"png-bytes",
        )
    )
    with session_factory() as session:
        result = SarasotaAuctionScraper(
            session=session,
            storage=LocalStorage(tmp_path),
            config=ScraperConfig(delay_between_pages_ms=0),
            client=client,
        ).scrape(url="https://example.test/source")

        batch = session.get(AuctionBatch, result.batch_id)
        snapshots = session.scalars(select(SourceSnapshot).where(SourceSnapshot.batch_id == result.batch_id)).all()
        record = session.scalar(select(AuctionRecord).where(AuctionRecord.batch_id == result.batch_id))

    assert client.calls == 1
    assert batch is not None
    assert batch.status == "completed"
    assert batch.records_valid == 1
    assert record is not None
    assert len(snapshots) == 1
    assert snapshots[0].html_path is not None
    assert snapshots[0].auction_record_id == record.id


def test_failed_page_load_produces_structured_error_and_failure_record(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    client = FakePageClient(
        PageLoadResult(
            requested_url="https://example.test/source",
            final_url=None,
            status="failed",
            error_message="timeout",
            attempts=2,
        )
    )
    with session_factory() as session:
        result = SarasotaAuctionScraper(
            session=session,
            storage=LocalStorage(tmp_path),
            config=ScraperConfig(delay_between_pages_ms=0),
            client=client,
        ).scrape(url="https://example.test/source")

        failure = session.scalar(select(ScraperFailure).where(ScraperFailure.batch_id == result.batch_id))

    assert result.batch_status == "failed"
    assert result.error_message == "timeout"
    assert failure is not None
    assert failure.retry_count == 1


def test_snapshot_only_mode_does_not_require_parser_success(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    client = FakePageClient(
        PageLoadResult(
            requested_url="https://example.test/source",
            final_url="https://example.test/source",
            status="success",
            http_status=200,
            page_title="Unparseable",
            html="<html><body><p>No auction fields yet</p></body></html>",
        )
    )
    with session_factory() as session:
        result = SarasotaAuctionScraper(
            session=session,
            storage=LocalStorage(tmp_path),
            config=ScraperConfig(delay_between_pages_ms=0),
            client=client,
        ).scrape(url="https://example.test/source", snapshot_only=True)

        batch = session.get(AuctionBatch, result.batch_id)
        snapshots = session.scalars(select(SourceSnapshot).where(SourceSnapshot.batch_id == result.batch_id)).all()

    assert batch is not None
    assert batch.status == "completed"
    assert batch.records_valid == 0
    assert batch.records_quarantined == 0
    assert len(snapshots) == 1


def test_blocked_markers_are_detected_without_bypass_attempts() -> None:
    reason = detect_blocked_reason(title="Access Denied", html="<html>captcha required</html>", http_status=403)

    assert reason is not None
    assert "blocked" in reason or "access" in reason.lower()
