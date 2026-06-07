from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.models import core  # noqa: F401
from app.models.core import AuctionBatch, AuctionRecord, SourceSnapshot, TriageResult
from app.services.fixture_import_service import import_sarasota_fixtures

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "fixtures/sarasota/html"


@pytest.fixture
def session_factory():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)


def test_import_sarasota_fixtures_persists_records_snapshots_and_triage(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(local_storage_root=tmp_path / ".storage")
    with session_factory() as session:
        result = import_sarasota_fixtures(
            session=session,
            fixtures_dir=FIXTURES_DIR,
            run_triage=True,
            settings=settings,
        )

    assert result.fixtures_processed == 4
    assert result.snapshots_stored == 4
    assert result.records_created == 4
    assert result.records_quarantined == 1
    assert result.triage_results_created == 4

    with session_factory() as session:
        batch = session.get(AuctionBatch, result.batch_id)
        assert batch is not None
        assert batch.status == "completed"
        assert batch.records_valid == 4
        assert (
            batch.records_research_candidates
            + batch.records_watchlist
            + batch.records_rejected
            + batch.records_manual_review
            + batch.records_quarantined
            > 0
        )

        records = list(session.scalars(select(AuctionRecord).where(AuctionRecord.batch_id == result.batch_id)).all())
        assert len(records) == 4
        triage_rows = list(
            session.scalars(
                select(TriageResult).where(TriageResult.auction_record_id.in_([record.id for record in records]))
            ).all()
        )
        assert len(triage_rows) == 4
        snapshots = list(
            session.scalars(select(SourceSnapshot).where(SourceSnapshot.batch_id == result.batch_id)).all()
        )
        assert len(snapshots) == 5
