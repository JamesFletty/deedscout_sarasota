from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.core import AuctionBatch
from app.scraping.playwright_client import ScraperConfig
from app.scraping.sarasota_auction_scraper import SarasotaAuctionScraper
from app.services.ambiguity_classifier_service import classify_ambiguous_records
from app.services.job_service import JobState, job_service
from app.services.triage_service import run_tier1_triage
from app.storage.factory import build_storage


class BatchNotFoundError(ValueError):
    """Raised when a requested auction batch does not exist."""


def create_sarasota_import_batch(
    *,
    session: Session,
    source_url: str | None,
    snapshot_only: bool,
    config_overrides: dict[str, object],
    settings: Settings | None = None,
) -> tuple[AuctionBatch, JobState]:
    active_settings = settings or get_settings()
    job = job_service.create_started(job_type="sarasota_import", message="Synchronous import job started")
    if source_url:
        config = _scraper_config(active_settings, config_overrides)
        result = SarasotaAuctionScraper(
            session=session,
            storage=build_storage(active_settings),
            config=config,
        ).scrape(url=source_url, snapshot_only=snapshot_only)
        batch = get_batch(session, result.batch_id)
        if result.error_message:
            job_service.fail(job.job_id, error_message=result.error_message)
        else:
            job_service.complete(
                job.job_id,
                batch_id=batch.id,
                message="Synchronous Sarasota snapshot import completed",
            )
        return batch, job_service.get(job.job_id)

    batch = AuctionBatch(
        county="Sarasota",
        source="manual_or_future_sarasota_import",
        status="created",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    session.add(batch)
    session.commit()
    session.refresh(batch)
    job_service.complete(job.job_id, batch_id=batch.id, message="Batch created; no source URL was provided")
    return batch, job_service.get(job.job_id)


def list_batches(
    session: Session,
    *,
    limit: int,
    offset: int,
    county: str | None = None,
    status: str | None = None,
) -> tuple[list[AuctionBatch], int]:
    query = select(AuctionBatch)
    count_query = select(func.count()).select_from(AuctionBatch)
    if county:
        query = query.where(AuctionBatch.county == county)
        count_query = count_query.where(AuctionBatch.county == county)
    if status:
        query = query.where(AuctionBatch.status == status)
        count_query = count_query.where(AuctionBatch.status == status)
    total = session.scalar(count_query) or 0
    items = list(session.scalars(query.order_by(AuctionBatch.created_at.desc()).offset(offset).limit(limit)).all())
    return items, total


def get_batch(session: Session, batch_id: UUID) -> AuctionBatch:
    batch = session.get(AuctionBatch, batch_id)
    if batch is None:
        raise BatchNotFoundError(f"Batch not found: {batch_id}")
    return batch


def run_batch_triage(
    *,
    session: Session,
    batch_id: UUID,
    include_llm_ambiguity_classifier: bool,
) -> tuple[AuctionBatch, int, int]:
    job = job_service.create_started(job_type="tier1_triage", batch_id=batch_id)
    results = run_tier1_triage(session, batch_id)
    attempted = 0
    if include_llm_ambiguity_classifier:
        summary = classify_ambiguous_records(session=session, batch_id=batch_id)
        attempted = summary.attempted
    batch = get_batch(session, batch_id)
    job_service.complete(job.job_id, batch_id=batch_id, message="Synchronous triage job completed")
    return batch, len(results), attempted


def _scraper_config(settings: Settings, overrides: dict[str, object]) -> ScraperConfig:
    base = ScraperConfig.from_settings(settings)
    return ScraperConfig(
        county=base.county,
        headless=_bool_override(overrides, "headless", base.headless),
        max_pages=_int_override(overrides, "max_pages", base.max_pages),
        max_retries=_int_override(overrides, "max_retries", base.max_retries),
        delay_between_pages_ms=_int_override(
            overrides,
            "delay_between_pages_ms",
            base.delay_between_pages_ms,
        ),
        timeout_ms=_int_override(overrides, "timeout_ms", base.timeout_ms),
        screenshot_enabled=_bool_override(overrides, "screenshot_enabled", base.screenshot_enabled),
        save_html_enabled=_bool_override(overrides, "save_html_enabled", base.save_html_enabled),
        user_agent=base.user_agent,
    )


def _int_override(overrides: dict[str, object], key: str, default: int) -> int:
    value = overrides.get(key)
    return default if value is None else int(str(value))


def _bool_override(overrides: dict[str, object], key: str, default: bool) -> bool:
    value = overrides.get(key)
    return default if value is None else bool(value)
