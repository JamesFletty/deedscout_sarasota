from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.core import AuctionBatch, AuctionRecord, SourceSnapshot
from app.parsing.fixture_paths import resolve_sarasota_fixtures_dir
from app.parsing.fixture_replay import replay_fixture
from app.schemas.auction import NormalizedAuctionRecord
from app.scraping.snapshotter import SnapshotResult, snapshot_page
from app.services.triage_service import run_tier1_triage
from app.storage.factory import build_storage


@dataclass(frozen=True)
class FixtureImportResult:
    batch_id: UUID
    fixtures_processed: int
    snapshots_stored: int
    records_created: int
    records_quarantined: int
    triage_results_created: int


def import_sarasota_fixtures(
    *,
    session: Session,
    fixtures_dir: Path | None = None,
    run_triage: bool = True,
    settings: Settings | None = None,
) -> FixtureImportResult:
    active_settings = settings or get_settings()
    resolved_dir = resolve_sarasota_fixtures_dir(fixtures_dir)
    storage = build_storage(active_settings)

    batch = AuctionBatch(
        county="Sarasota",
        source=f"fixtures:{resolved_dir}",
        status="running",
        started_at=datetime.now(UTC),
    )
    session.add(batch)
    session.flush()

    fixtures_processed = 0
    snapshots_stored = 0
    records_created = 0
    records_quarantined = 0

    for fixture_path in sorted(resolved_dir.glob("*.html")):
        fixtures_processed += 1
        html = fixture_path.read_text(encoding="utf-8")
        replay = replay_fixture(fixture_path)
        source_url = _fixture_source_url(fixture_path, replay.records)
        snapshot = snapshot_page(
            session=session,
            storage=storage,
            batch_id=batch.id,
            source_url=source_url,
            html=html,
            screenshot_bytes=None,
            save_html=active_settings.scraper_save_html_enabled,
            save_screenshot=False,
        )
        snapshots_stored += 1

        created_ids = _persist_records(session, batch.id, replay.records)
        records_created += len(created_ids)
        records_quarantined += len(replay.quarantined_records)
        _link_snapshot_to_records(session, snapshot, created_ids)

    batch.status = "completed"
    batch.completed_at = datetime.now(UTC)
    batch.records_found = records_created + records_quarantined
    batch.records_valid = records_created
    batch.records_quarantined = records_quarantined
    session.commit()

    triage_results_created = 0
    if run_triage and records_created > 0:
        triage_results = run_tier1_triage(session, batch.id)
        triage_results_created = len(triage_results)

    return FixtureImportResult(
        batch_id=batch.id,
        fixtures_processed=fixtures_processed,
        snapshots_stored=snapshots_stored,
        records_created=records_created,
        records_quarantined=records_quarantined,
        triage_results_created=triage_results_created,
    )


def _fixture_source_url(fixture_path: Path, records: tuple[NormalizedAuctionRecord, ...]) -> str:
    for record in records:
        if record.detail_url:
            return record.detail_url
    return f"fixture://sarasota/{fixture_path.name}"


def _persist_records(
    session: Session,
    batch_id: UUID,
    records: tuple[NormalizedAuctionRecord, ...],
) -> list[UUID]:
    created_ids: list[UUID] = []
    for record in records:
        auction_record = AuctionRecord(
            batch_id=batch_id,
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
        session.add(auction_record)
        session.flush()
        created_ids.append(auction_record.id)
    return created_ids


def _link_snapshot_to_records(
    session: Session,
    snapshot: SnapshotResult,
    record_ids: list[UUID],
) -> None:
    if not record_ids:
        return

    snapshot.snapshot.auction_record_id = record_ids[0]
    base = snapshot.snapshot
    for record_id in record_ids[1:]:
        session.add(
            SourceSnapshot(
                auction_record_id=record_id,
                batch_id=base.batch_id,
                source_url=base.source_url,
                html_path=base.html_path,
                screenshot_path=base.screenshot_path,
                content_hash=base.content_hash,
                page_structure_hash=base.page_structure_hash,
                parser_version=base.parser_version,
                scraped_at=base.scraped_at,
            )
        )
