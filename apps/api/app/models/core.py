import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base

JsonList = list[Any]
JsonDict = dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(UTC)


JSONVariant = JSON().with_variant(JSONB, "postgresql")


class AuctionBatch(Base):
    __tablename__ = "auction_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    county: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_valid: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_quarantined: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_watchlist: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_research_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_manual_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    records: Mapped[list["AuctionRecord"]] = relationship(back_populates="batch")


class AuctionRecord(Base):
    __tablename__ = "auction_records"
    __table_args__ = (
        Index("ix_auction_records_batch_id", "batch_id"),
        Index("ix_auction_records_parcel_id_normalized", "parcel_id_normalized"),
        Index("ix_auction_records_auction_status", "auction_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("auction_batches.id"), nullable=False)
    county: Mapped[str] = mapped_column(Text, nullable=False)
    case_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    parcel_id_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    parcel_id_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    auction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auction_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    opening_bid_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    appraiser_assessment_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    detail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_deed_record_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    missing_fields: Mapped[JsonList] = mapped_column(JSONVariant, nullable=False, default=list)
    parse_warnings: Mapped[JsonList] = mapped_column(JSONVariant, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    batch: Mapped[AuctionBatch] = relationship(back_populates="records")
    snapshots: Mapped[list["SourceSnapshot"]] = relationship(back_populates="auction_record")
    triage_results: Mapped[list["TriageResult"]] = relationship(back_populates="auction_record")


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (Index("ix_source_snapshots_batch_id", "batch_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    auction_record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_records.id"), nullable=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_batches.id"), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    html_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_structure_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    auction_record: Mapped[AuctionRecord | None] = relationship(back_populates="snapshots")


class TriageResult(Base):
    __tablename__ = "triage_results"
    __table_args__ = (
        Index("ix_triage_results_auction_record_id", "auction_record_id"),
        Index("ix_triage_results_tier_1_status", "tier_1_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    auction_record_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("auction_records.id"), nullable=False)
    tier_1_status: Mapped[str] = mapped_column(Text, nullable=False)
    grade: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_spread_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    opening_bid_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    data_quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    risk_flags: Mapped[JsonList] = mapped_column(JSONVariant, nullable=False, default=list)
    positive_signals: Mapped[JsonList] = mapped_column(JSONVariant, nullable=False, default=list)
    evidence: Mapped[JsonList] = mapped_column(JSONVariant, nullable=False, default=list)
    recommended_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    llm_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    auction_record: Mapped[AuctionRecord] = relationship(back_populates="triage_results")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("ix_agent_runs_batch_id", "batch_id"),
        Index("ix_agent_runs_auction_record_id", "auction_record_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_batches.id"), nullable=True)
    auction_record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_records.id"), nullable=True)
    agent_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[JsonDict] = mapped_column(JSONVariant, nullable=False)
    output_json: Mapped[JsonDict | None] = mapped_column(JSONVariant, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CostEvent(Base):
    __tablename__ = "cost_events"
    __table_args__ = (
        Index("ix_cost_events_batch_id", "batch_id"),
        Index("ix_cost_events_auction_record_id", "auction_record_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_batches.id"), nullable=True)
    auction_record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_records.id"), nullable=True)
    service: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    unit_count: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    metadata_json: Mapped[JsonDict] = mapped_column("metadata", JSONVariant, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class ScraperFailure(Base):
    __tablename__ = "scraper_failures"
    __table_args__ = (Index("ix_scraper_failures_batch_id", "batch_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), ForeignKey("auction_batches.id"), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
