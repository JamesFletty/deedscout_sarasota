from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.core import AuctionBatch, AuctionRecord, ScraperFailure
from app.parsing.fixture_replay import replay_fixture
from app.scraping.playwright_client import PageClient, PlaywrightPageClient, ScraperConfig
from app.scraping.rate_limiter import RateLimiter
from app.scraping.sarasota_source_discovery import SourceDiscoveryResult, discover_sarasota_source
from app.scraping.snapshotter import SnapshotResult, snapshot_page
from app.storage.base import StorageBackend


@dataclass(frozen=True)
class SarasotaScrapeResult:
    batch_id: UUID
    batch_status: str
    discovery: SourceDiscoveryResult
    snapshot: SnapshotResult | None
    records_created: int
    records_quarantined: int
    error_message: str | None = None


class SarasotaAuctionScraper:
    def __init__(
        self,
        *,
        session: Session,
        storage: StorageBackend,
        config: ScraperConfig,
        client: PageClient | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.config = config
        self.client = client or PlaywrightPageClient(config)
        self.rate_limiter = RateLimiter(config.delay_between_pages_ms)

    def scrape(self, *, url: str, snapshot_only: bool = False) -> SarasotaScrapeResult:
        batch = AuctionBatch(
            county="Sarasota",
            source=url,
            status="running",
            started_at=datetime.now(UTC),
        )
        self.session.add(batch)
        self.session.flush()

        discovery = discover_sarasota_source(url, self.client)
        snapshot: SnapshotResult | None = None
        records_created = 0
        records_quarantined = 0
        created_record_ids: list[UUID] = []
        error_message: str | None = None

        if discovery.page_result.html:
            snapshot = snapshot_page(
                session=self.session,
                storage=self.storage,
                batch_id=batch.id,
                source_url=discovery.final_url or url,
                html=discovery.page_result.html,
                screenshot_bytes=discovery.page_result.screenshot_bytes,
                save_html=self.config.save_html_enabled,
                save_screenshot=self.config.screenshot_enabled,
            )

        if discovery.source_status in {"blocked", "failed", "changed"}:
            error_message = "; ".join(discovery.notes) or f"Source {discovery.source_status}"
            if discovery.source_status in {"blocked", "failed"}:
                self.session.add(
                    ScraperFailure(
                        batch_id=batch.id,
                        source_url=url,
                        error_message=error_message,
                        retry_count=max(discovery.page_result.attempts - 1, 0),
                    )
                )
            batch.status = discovery.source_status
        else:
            if not snapshot_only and snapshot is not None and snapshot.html_artifact is not None:
                replay = replay_fixture(snapshot.html_artifact.uri)
                for record in replay.records:
                    auction_record = AuctionRecord(
                        batch_id=batch.id,
                        county=record.county,
                        case_number=record.case_number,
                        parcel_id_raw=record.parcel_id_raw,
                        parcel_id_normalized=record.parcel_id_normalized,
                        auction_date=record.auction_date,
                        auction_status=record.auction_status,
                        opening_bid_cents=record.opening_bid_cents,
                        appraiser_assessment_cents=record.appraiser_assessment_cents,
                        detail_url=record.detail_url,
                        notice_url=record.notice_url,
                        tax_deed_record_url=record.tax_deed_record_url,
                        parse_confidence=Decimal(str(record.parse_confidence)),
                        missing_fields=list(record.missing_fields),
                        parse_warnings=list(record.parse_warnings),
                    )
                    self.session.add(auction_record)
                    self.session.flush()
                    created_record_ids.append(auction_record.id)
                    records_created += 1
                if snapshot is not None and len(created_record_ids) == 1:
                    snapshot.snapshot.auction_record_id = created_record_ids[0]
                records_quarantined = len(replay.quarantined_records)
            batch.status = "completed"

        batch.completed_at = datetime.now(UTC)
        batch.records_found = records_created + records_quarantined
        batch.records_valid = records_created
        batch.records_quarantined = records_quarantined
        batch.error_message = error_message
        self.session.commit()
        if snapshot is not None:
            _ = snapshot.snapshot.id
            _ = snapshot.snapshot.html_path
            _ = snapshot.snapshot.screenshot_path

        return SarasotaScrapeResult(
            batch_id=batch.id,
            batch_status=batch.status,
            discovery=discovery,
            snapshot=snapshot,
            records_created=records_created,
            records_quarantined=records_quarantined,
            error_message=error_message,
        )
