from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.api import JobResponse
from app.services.job_service import job_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get synchronous job status",
    description="Returns status for the minimal in-process synchronous job facade used by the MVP.",
)
def get_job(job_id: UUID) -> JobResponse:
    try:
        job = job_service.get(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)}) from exc
    return JobResponse(**job.__dict__)
