from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import core  # noqa: F401
from app.models.core import TriageResult
from app.parsing.fixture_replay import replay_fixture, replay_fixtures, write_expected_snapshot
from app.scraping.playwright_client import ScraperConfig
from app.scraping.sarasota_auction_scraper import SarasotaAuctionScraper, SarasotaScrapeResult
from app.services.ambiguity_classifier_service import AmbiguityClassificationSummary, classify_ambiguous_records
from app.services.fixture_import_service import FixtureImportResult, import_sarasota_fixtures
from app.services.triage_service import run_tier1_triage
from app.storage.factory import build_storage

DEFAULT_EXPECTED_DIR = Path("fixtures/sarasota/expected")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("replay-fixture", help="Replay one saved Sarasota HTML fixture")
    single.add_argument("path", type=Path)
    single.add_argument("--write-expected", action="store_true")
    single.add_argument("--expected-dir", type=Path, default=DEFAULT_EXPECTED_DIR)

    multiple = subparsers.add_parser("replay-fixtures", help="Replay all saved Sarasota HTML fixtures in a directory")
    multiple.add_argument("path", type=Path)
    multiple.add_argument("--write-expected", action="store_true")
    multiple.add_argument("--expected-dir", type=Path, default=DEFAULT_EXPECTED_DIR)

    scrape = subparsers.add_parser("scrape-sarasota", help="Conservatively snapshot a configured Sarasota source URL")
    scrape.add_argument("--url", required=True)
    scrape.add_argument("--headful", action="store_true")
    scrape.add_argument("--max-pages", type=int)
    scrape.add_argument("--snapshot-only", action="store_true")

    triage = subparsers.add_parser("triage-batch", help="Run deterministic Tier 1 triage for a batch")
    triage.add_argument("batch_id")

    classify = subparsers.add_parser("classify-ambiguous", help="Run cost-gated LLM ambiguity classification")
    classify.add_argument("batch_id")

    import_fixtures = subparsers.add_parser(
        "import-fixtures",
        help="Import committed Sarasota HTML fixtures into a batch and optionally run triage",
    )
    import_fixtures.add_argument("--fixtures-dir", type=Path)
    import_fixtures.add_argument("--no-triage", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "replay-fixture":
        replay_result = replay_fixture(args.path)
        if args.write_expected:
            write_expected_snapshot(replay_result, args.path, expected_dir=args.expected_dir)
        print(json.dumps(replay_result.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    elif args.command == "replay-fixtures":
        result = replay_fixtures(args.path)
        if args.write_expected:
            for fixture_path in sorted(args.path.glob("*.html")):
                write_expected_snapshot(replay_fixture(fixture_path), fixture_path, expected_dir=args.expected_dir)
        print(json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    elif args.command == "scrape-sarasota":
        settings = get_settings()
        config = _scraper_config_from_args(settings, headful=args.headful, max_pages=args.max_pages)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            scrape_result = SarasotaAuctionScraper(
                session=session,
                storage=build_storage(settings),
                config=config,
            ).scrape(url=args.url, snapshot_only=args.snapshot_only)
        print(json.dumps(_scrape_result_payload(scrape_result), indent=2, sort_keys=True))
        return 0
    elif args.command == "triage-batch":
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            triage_results = run_tier1_triage(session, UUID(args.batch_id))
        print(json.dumps(_triage_result_payload(triage_results), indent=2, sort_keys=True))
        return 0
    elif args.command == "import-fixtures":
        settings = get_settings()
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            import_result = import_sarasota_fixtures(
                session=session,
                fixtures_dir=args.fixtures_dir or settings.sarasota_fixtures_dir,
                run_triage=not args.no_triage,
                settings=settings,
            )
        print(json.dumps(_fixture_import_payload(import_result), indent=2, sort_keys=True))
        return 0
    else:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            summary = classify_ambiguous_records(session=session, batch_id=UUID(args.batch_id))
        print(json.dumps(_classification_summary_payload(summary), indent=2, sort_keys=True))
        return 0

    raise RuntimeError(f"Unhandled CLI command: {args.command}")


def _scraper_config_from_args(settings: Settings, *, headful: bool, max_pages: int | None) -> ScraperConfig:
    config = ScraperConfig.from_settings(settings)
    return ScraperConfig(
        county=config.county,
        headless=not headful,
        max_pages=max_pages or config.max_pages,
        max_retries=config.max_retries,
        delay_between_pages_ms=config.delay_between_pages_ms,
        timeout_ms=config.timeout_ms,
        screenshot_enabled=config.screenshot_enabled,
        save_html_enabled=config.save_html_enabled,
        user_agent=config.user_agent,
    )


def _scrape_result_payload(scrape_result: SarasotaScrapeResult) -> dict[str, object]:
    snapshot = scrape_result.snapshot
    return {
        "batch_id": str(scrape_result.batch_id),
        "batch_status": scrape_result.batch_status,
        "source_status": scrape_result.discovery.source_status,
        "requested_url": scrape_result.discovery.requested_url,
        "final_url": scrape_result.discovery.final_url,
        "http_status": scrape_result.discovery.http_status,
        "page_title": scrape_result.discovery.page_title,
        "notes": list(scrape_result.discovery.notes),
        "records_created": scrape_result.records_created,
        "records_quarantined": scrape_result.records_quarantined,
        "error_message": scrape_result.error_message,
        "snapshot_id": str(snapshot.snapshot.id) if snapshot is not None else None,
        "html_path": snapshot.snapshot.html_path if snapshot is not None else None,
        "screenshot_path": snapshot.snapshot.screenshot_path if snapshot is not None else None,
    }


def _triage_result_payload(triage_results: list[TriageResult]) -> dict[str, object]:
    return {
        "results": [
            {
                "auction_record_id": str(result.auction_record_id),
                "tier_1_status": result.tier_1_status,
                "grade": result.grade,
                "estimated_spread_cents": result.estimated_spread_cents,
                "opening_bid_ratio": str(result.opening_bid_ratio) if result.opening_bid_ratio is not None else None,
                "data_quality_score": str(result.data_quality_score),
                "llm_calls_used": result.llm_calls_used,
                "estimated_cost_usd": str(result.estimated_cost_usd),
            }
            for result in triage_results
        ]
    }


def _fixture_import_payload(result: FixtureImportResult) -> dict[str, object]:
    return {
        "batch_id": str(result.batch_id),
        "fixtures_processed": result.fixtures_processed,
        "snapshots_stored": result.snapshots_stored,
        "records_created": result.records_created,
        "records_quarantined": result.records_quarantined,
        "triage_results_created": result.triage_results_created,
    }


def _classification_summary_payload(summary: AmbiguityClassificationSummary) -> dict[str, object]:
    return {
        "attempted": summary.attempted,
        "skipped": summary.skipped,
        "updated": summary.updated,
        "cost_cap_skipped": summary.cost_cap_skipped,
        "agent_runs": len(summary.agent_runs),
        "cost_events": len(summary.cost_events),
    }


if __name__ == "__main__":
    raise SystemExit(main())
