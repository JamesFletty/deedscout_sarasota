from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.core import AgentRun, AuctionRecord, CostEvent, SourceSnapshot, TriageResult


class RecordNotFoundError(ValueError):
    """Raised when a requested auction record does not exist."""


def get_latest_triage(session: Session, record_id: UUID) -> TriageResult | None:
    return session.scalar(
        select(TriageResult)
        .where(TriageResult.auction_record_id == record_id)
        .order_by(TriageResult.created_at.desc())
        .limit(1)
    )


def list_batch_records(
    session: Session,
    *,
    batch_id: UUID,
    limit: int,
    offset: int,
    tier_1_status: str | None = None,
    grade: str | None = None,
    auction_status: str | None = None,
    search: str | None = None,
) -> tuple[list[tuple[AuctionRecord, TriageResult | None]], int]:
    query = select(AuctionRecord).where(AuctionRecord.batch_id == batch_id)
    count_query = select(func.count()).select_from(AuctionRecord).where(AuctionRecord.batch_id == batch_id)
    if auction_status:
        query = query.where(AuctionRecord.auction_status == auction_status)
        count_query = count_query.where(AuctionRecord.auction_status == auction_status)
    if search:
        pattern = f"%{search}%"
        predicate = or_(AuctionRecord.parcel_id_normalized.like(pattern), AuctionRecord.case_number.like(pattern))
        query = query.where(predicate)
        count_query = count_query.where(predicate)

    records = list(session.scalars(query.order_by(AuctionRecord.created_at.desc()).offset(offset).limit(limit)).all())
    rows = [(record, get_latest_triage(session, record.id)) for record in records]
    if tier_1_status:
        rows = [(record, triage) for record, triage in rows if triage and triage.tier_1_status == tier_1_status]
    if grade:
        rows = [(record, triage) for record, triage in rows if triage and triage.grade == grade]
    total = session.scalar(count_query) or 0
    if tier_1_status or grade:
        total = len(rows)
    return rows, total


def get_record_with_triage(session: Session, record_id: UUID) -> tuple[AuctionRecord, TriageResult | None]:
    record = session.get(AuctionRecord, record_id)
    if record is None:
        raise RecordNotFoundError(f"Record not found: {record_id}")
    return record, get_latest_triage(session, record.id)


def get_record_evidence(
    session: Session,
    record_id: UUID,
    settings: Settings | None = None,
) -> tuple[list[SourceSnapshot], list[dict[str, object]], list[AgentRun], list[CostEvent]]:
    record = session.get(AuctionRecord, record_id)
    if record is None:
        raise RecordNotFoundError(f"Record not found: {record_id}")
    snapshots = list(session.scalars(select(SourceSnapshot).where(SourceSnapshot.auction_record_id == record_id)).all())
    triage_results = list(
        session.scalars(select(TriageResult).where(TriageResult.auction_record_id == record_id)).all()
    )
    evidence: list[dict[str, object]] = []
    for result in triage_results:
        evidence.extend(dict(item) for item in result.evidence)
    agent_runs = list(session.scalars(select(AgentRun).where(AgentRun.auction_record_id == record_id)).all())
    cost_events = list(session.scalars(select(CostEvent).where(CostEvent.auction_record_id == record_id)).all())
    active_settings = settings or get_settings()
    if active_settings.app_env not in {"local", "development", "dev", "test"}:
        for snapshot in snapshots:
            snapshot.html_path = None
            snapshot.screenshot_path = None
    return snapshots, evidence, agent_runs, cost_events
