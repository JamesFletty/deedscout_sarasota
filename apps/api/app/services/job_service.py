from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

JobStatus = Literal["pending", "running", "completed", "failed"]


@dataclass
class JobState:
    job_id: UUID
    job_type: str
    status: JobStatus
    batch_id: UUID | None = None
    message: str | None = None
    error_message: str | None = None
    created_at: datetime = datetime.now(UTC)
    completed_at: datetime | None = None


class InMemoryJobService:
    def __init__(self) -> None:
        self._jobs: dict[UUID, JobState] = {}

    def create_started(self, *, job_type: str, batch_id: UUID | None = None, message: str | None = None) -> JobState:
        job = JobState(
            job_id=uuid.uuid4(),
            job_type=job_type,
            status="running",
            batch_id=batch_id,
            message=message,
            created_at=datetime.now(UTC),
        )
        self._jobs[job.job_id] = job
        return job

    def complete(self, job_id: UUID, *, batch_id: UUID | None = None, message: str | None = None) -> JobState:
        job = self.get(job_id)
        job.status = "completed"
        job.batch_id = batch_id or job.batch_id
        job.message = message or job.message
        job.completed_at = datetime.now(UTC)
        return job

    def fail(self, job_id: UUID, *, error_message: str) -> JobState:
        job = self.get(job_id)
        job.status = "failed"
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        return job

    def get(self, job_id: UUID) -> JobState:
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Job not found: {job_id}")
        return job


job_service = InMemoryJobService()
