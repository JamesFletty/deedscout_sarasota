from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import (
    BatchListResponse,
    BatchSummary,
    ClassificationRunResponse,
    ImportBatchResponse,
    SarasotaImportRequest,
    TriageRunRequest,
    TriageRunResponse,
)
from app.services.ambiguity_classifier_service import classify_ambiguous_records
from app.services.batch_service import (
    BatchNotFoundError,
    create_sarasota_import_batch,
    get_batch,
    list_batches,
    run_batch_triage,
)

router = APIRouter(prefix="/api/batches", tags=["batches"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/sarasota/import",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Sarasota import batch",
    description=(
        "Creates a synchronous job-like Sarasota import batch. "
        "If a source URL is supplied, the scraper snapshots it."
    ),
)
def create_sarasota_import(request: SarasotaImportRequest, db: DbSession) -> ImportBatchResponse:
    overrides = request.model_dump(exclude={"source_url", "snapshot_only"}, exclude_none=True)
    try:
        batch, job = create_sarasota_import_batch(
            session=db,
            source_url=request.source_url,
            snapshot_only=request.snapshot_only,
            config_overrides=overrides,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
    return ImportBatchResponse(batch_id=batch.id, job_id=job.job_id, job_status=job.status)


@router.get(
    "",
    response_model=BatchListResponse,
    summary="List recent auction batches",
    description="Lists recent batches with optional county/status filtering and pagination.",
)
def get_batches(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    county: str | None = None,
    status: str | None = None,
) -> BatchListResponse:
    items, total = list_batches(db, limit=limit, offset=offset, county=county, status=status)
    return BatchListResponse(
        items=[BatchSummary.model_validate(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/{batch_id}",
    response_model=BatchSummary,
    summary="Get one batch summary",
    description="Returns batch metadata and record/triage/cost counters.",
)
def get_batch_summary(batch_id: UUID, db: DbSession) -> BatchSummary:
    try:
        return BatchSummary.model_validate(get_batch(db, batch_id))
    except BatchNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc


@router.post(
    "/{batch_id}/triage",
    response_model=TriageRunResponse,
    summary="Run deterministic Tier 1 triage",
    description="Runs deterministic triage first and optionally follows with eligible LLM ambiguity classification.",
)
def run_triage(batch_id: UUID, request: TriageRunRequest, db: DbSession) -> TriageRunResponse:
    try:
        batch, created, attempted = run_batch_triage(
            session=db,
            batch_id=batch_id,
            include_llm_ambiguity_classifier=request.include_llm_ambiguity_classifier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    return TriageRunResponse(
        batch=BatchSummary.model_validate(batch),
        triage_results_created=created,
        ambiguity_classifier_attempted=attempted,
    )


@router.post(
    "/{batch_id}/classify-ambiguous",
    response_model=ClassificationRunResponse,
    summary="Run LLM ambiguity classifier",
    description="Runs the cost-gated provider-agnostic classifier only for eligible ambiguous triage results.",
)
def classify_ambiguous(batch_id: UUID, db: DbSession) -> ClassificationRunResponse:
    try:
        get_batch(db, batch_id)
        summary = classify_ambiguous_records(session=db, batch_id=batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    return ClassificationRunResponse(
        attempted=summary.attempted,
        skipped=summary.skipped,
        updated=summary.updated,
        cost_cap_skipped=summary.cost_cap_skipped,
        agent_runs=len(summary.agent_runs),
        cost_events=len(summary.cost_events),
    )
