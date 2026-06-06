from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import core  # noqa: F401
from app.models.core import AgentRun, AuctionBatch, AuctionRecord, CostEvent, SourceSnapshot, TriageResult
from app.schemas.api import SarasotaImportRequest


@pytest.fixture
def api_client() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.clear()


def seed_batch(factory: sessionmaker[Session]) -> tuple[str, str]:
    with factory() as session:
        batch = AuctionBatch(county="Sarasota", source="fixture", status="completed", started_at=core.utc_now())
        session.add(batch)
        session.flush()
        record = AuctionRecord(
            batch_id=batch.id,
            county="Sarasota",
            case_number="2026-TD-001",
            parcel_id_raw="0123-45-6789",
            parcel_id_normalized="0123456789",
            auction_status="scheduled",
            opening_bid_cents=5_000_000,
            appraiser_assessment_cents=20_000_000,
            parse_confidence=Decimal("0.9500"),
            missing_fields=[],
            parse_warnings=[],
        )
        session.add(record)
        session.flush()
        snapshot = SourceSnapshot(
            auction_record_id=record.id,
            batch_id=batch.id,
            source_url="https://example.test/detail",
            html_path="/.storage/internal.html",
            screenshot_path="/.storage/internal.png",
            content_hash="a" * 64,
            page_structure_hash="b" * 64,
            parser_version="test-parser",
            scraped_at=core.utc_now(),
        )
        triage = TriageResult(
            auction_record_id=record.id,
            tier_1_status="WATCHLIST",
            grade="C",
            estimated_spread_cents=15_000_000,
            opening_bid_ratio=Decimal("0.2500"),
            data_quality_score=Decimal("0.9000"),
            risk_flags=["ambiguous_junk:ROAD"],
            positive_signals=[],
            evidence=[
                {
                    "rule_name": "fixture",
                    "field_inspected": "property_text",
                    "value": "ROAD TRACT",
                    "decision_impact": "manual_review",
                    "reason": "Ambiguous fixture evidence.",
                }
            ],
            recommended_next_action="Watchlist for human review.",
            requires_human_review=True,
            llm_calls_used=0,
            estimated_cost_usd=Decimal("0"),
        )
        run = AgentRun(
            batch_id=batch.id,
            auction_record_id=record.id,
            agent_name="fixture_agent",
            status="completed",
            input_json={},
            output_json={"ok": True},
            started_at=core.utc_now(),
            completed_at=core.utc_now(),
        )
        cost = CostEvent(
            batch_id=batch.id,
            auction_record_id=record.id,
            service="fixture",
            event_type="fixture_event",
            unit_count=Decimal("1"),
            estimated_cost_usd=Decimal("0"),
            metadata_json={"safe": True},
        )
        session.add_all([snapshot, triage, run, cost])
        session.commit()
        return str(batch.id), str(record.id)


def test_import_batch_and_job_status(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client
    response = client.post("/api/batches/sarasota/import", json={"snapshot_only": True})

    assert response.status_code == 201
    payload = response.json()
    assert payload["batch_id"]
    assert payload["job_id"]
    assert payload["job_status"] == "completed"

    job_response = client.get(f"/api/jobs/{payload['job_id']}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "completed"


def test_import_request_parses_supplied_sources_by_default() -> None:
    request = SarasotaImportRequest(source_url="file:///workspace/fixtures/sarasota/html/sample_auction_detail.html")

    assert request.snapshot_only is False


def test_batches_can_be_listed_and_inspected(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api_client
    batch_id, _ = seed_batch(factory)

    list_response = client.get("/api/batches", params={"county": "Sarasota"})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = client.get(f"/api/batches/{batch_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == batch_id


def test_batch_records_filters_and_record_detail(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api_client
    batch_id, record_id = seed_batch(factory)

    records_response = client.get(
        f"/api/batches/{batch_id}/records",
        params={"tier_1_status": "WATCHLIST", "search": "012345"},
    )
    assert records_response.status_code == 200
    items = records_response.json()["items"]
    assert len(items) == 1
    assert items[0]["latest_triage"]["tier_1_status"] == "WATCHLIST"

    record_response = client.get(f"/api/records/{record_id}")
    assert record_response.status_code == 200
    assert record_response.json()["case_number"] == "2026-TD-001"


def test_record_evidence_endpoint(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api_client
    _, record_id = seed_batch(factory)

    response = client.get(f"/api/records/{record_id}/evidence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshots"][0]["source_url"] == "https://example.test/detail"
    assert payload["triage_evidence"][0]["rule_name"] == "fixture"
    assert payload["agent_runs"][0]["agent_name"] == "fixture_agent"
    assert payload["cost_events"][0]["service"] == "fixture"


def test_triage_and_classify_endpoints(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, factory = api_client
    batch_id, _ = seed_batch(factory)

    triage_response = client.post(f"/api/batches/{batch_id}/triage", json={"include_llm_ambiguity_classifier": False})
    assert triage_response.status_code == 200
    assert triage_response.json()["triage_results_created"] == 1

    classify_response = client.post(f"/api/batches/{batch_id}/classify-ambiguous")
    assert classify_response.status_code == 200
    assert "attempted" in classify_response.json()


def test_health_and_openapi_load(api_client: tuple[TestClient, sessionmaker[Session]]) -> None:
    client, _ = api_client

    assert client.get("/health").status_code == 200
    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["title"] == "DeedScout Sarasota API"
