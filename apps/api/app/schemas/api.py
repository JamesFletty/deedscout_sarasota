from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SarasotaImportRequest(BaseModel):
    source_url: str | None = None
    snapshot_only: bool = True
    headless: bool | None = None
    max_pages: int | None = Field(default=None, ge=1)
    max_retries: int | None = Field(default=None, ge=0)
    delay_between_pages_ms: int | None = Field(default=None, ge=0)
    timeout_ms: int | None = Field(default=None, gt=0)
    screenshot_enabled: bool | None = None
    save_html_enabled: bool | None = None


class JobResponse(BaseModel):
    job_id: UUID
    job_type: str
    status: Literal["pending", "running", "completed", "failed"]
    batch_id: UUID | None = None
    message: str | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ImportBatchResponse(BaseModel):
    batch_id: UUID
    job_id: UUID
    job_status: str


class BatchSummary(BaseModel):
    id: UUID
    county: str
    source: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    records_found: int
    records_valid: int
    records_quarantined: int
    records_rejected: int
    records_watchlist: int
    records_research_candidates: int
    records_manual_review: int
    llm_calls_used: int
    estimated_cost_usd: Decimal
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchListResponse(BaseModel):
    items: list[BatchSummary]
    limit: int
    offset: int
    total: int


class TriageSummary(BaseModel):
    tier_1_status: str
    grade: str
    estimated_spread_cents: int | None
    opening_bid_ratio: Decimal | None
    data_quality_score: Decimal
    risk_flags: list[object]
    positive_signals: list[object]
    recommended_next_action: str
    requires_human_review: bool
    llm_calls_used: int
    estimated_cost_usd: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuctionRecordResponse(BaseModel):
    id: UUID
    batch_id: UUID
    county: str
    case_number: str | None
    parcel_id_raw: str | None
    parcel_id_normalized: str | None
    auction_date: date | None
    auction_status: str | None
    opening_bid_cents: int | None
    appraiser_assessment_cents: int | None
    detail_url: str | None
    notice_url: str | None
    tax_deed_record_url: str | None
    parse_confidence: Decimal
    missing_fields: list[object]
    parse_warnings: list[object]
    created_at: datetime
    latest_triage: TriageSummary | None = None

    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    items: list[AuctionRecordResponse]
    limit: int
    offset: int
    total: int


class TriageRunRequest(BaseModel):
    include_llm_ambiguity_classifier: bool = False


class TriageRunResponse(BaseModel):
    batch: BatchSummary
    triage_results_created: int
    ambiguity_classifier_attempted: int = 0


class ClassificationRunResponse(BaseModel):
    attempted: int
    skipped: int
    updated: int
    cost_cap_skipped: int
    agent_runs: int
    cost_events: int


class SourceSnapshotResponse(BaseModel):
    id: UUID
    source_url: str
    html_path: str | None
    screenshot_path: str | None
    content_hash: str
    page_structure_hash: str | None
    parser_version: str
    scraped_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunResponse(BaseModel):
    id: UUID
    agent_name: str
    status: str
    output_json: dict[str, object] | None
    error_message: str | None
    model_name: str | None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: Decimal
    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CostEventResponse(BaseModel):
    id: UUID
    service: str
    event_type: str
    unit_count: Decimal
    estimated_cost_usd: Decimal
    metadata_json: dict[str, object]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordEvidenceResponse(BaseModel):
    record_id: UUID
    snapshots: list[SourceSnapshotResponse]
    triage_evidence: list[dict[str, object]]
    agent_runs: list[AgentRunResponse]
    cost_events: list[CostEventResponse]
