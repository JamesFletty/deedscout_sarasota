from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import (
    AgentRunResponse,
    AuctionRecordResponse,
    CostEventResponse,
    RecordEvidenceResponse,
    RecordListResponse,
    SourceSnapshotResponse,
    TriageSummary,
)
from app.services.record_service import (
    RecordNotFoundError,
    get_record_evidence,
    get_record_with_triage,
    list_batch_records,
)

router = APIRouter(tags=["records"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/api/batches/{batch_id}/records",
    response_model=RecordListResponse,
    summary="List records in a batch",
    description="Returns normalized records joined with the latest triage result and supports status/search filters.",
)
def get_batch_records(
    batch_id: UUID,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    tier_1_status: str | None = None,
    grade: str | None = None,
    auction_status: str | None = None,
    search: str | None = None,
) -> RecordListResponse:
    rows, total = list_batch_records(
        db,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
        tier_1_status=tier_1_status,
        grade=grade,
        auction_status=auction_status,
        search=search,
    )
    return RecordListResponse(
        items=[_record_response(record, triage) for record, triage in rows],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/api/records/{record_id}",
    response_model=AuctionRecordResponse,
    summary="Get one normalized auction record",
    description="Returns the normalized auction record and its latest triage result when available.",
)
def get_record(record_id: UUID, db: DbSession) -> AuctionRecordResponse:
    try:
        record, triage = get_record_with_triage(db, record_id)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    return _record_response(record, triage)


@router.get(
    "/api/records/{record_id}/evidence",
    response_model=RecordEvidenceResponse,
    summary="Get record evidence",
    description="Returns source snapshots, triage evidence, agent runs, and cost events for a record.",
)
def get_evidence(record_id: UUID, db: DbSession) -> RecordEvidenceResponse:
    try:
        snapshots, triage_evidence, agent_runs, cost_events = get_record_evidence(db, record_id)
    except RecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    return RecordEvidenceResponse(
        record_id=record_id,
        snapshots=[SourceSnapshotResponse.model_validate(snapshot) for snapshot in snapshots],
        triage_evidence=triage_evidence,
        agent_runs=[AgentRunResponse.model_validate(run) for run in agent_runs],
        cost_events=[CostEventResponse.model_validate(event) for event in cost_events],
    )


def _record_response(record, triage) -> AuctionRecordResponse:  # type: ignore[no-untyped-def]
    response = AuctionRecordResponse.model_validate(record)
    return response.model_copy(update={"latest_triage": TriageSummary.model_validate(triage) if triage else None})
