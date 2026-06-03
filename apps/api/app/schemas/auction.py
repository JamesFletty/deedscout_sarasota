from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AuctionStatus = Literal["scheduled", "running", "closed", "canceled", "postponed", "redeemed", "unknown"]


class NormalizedAuctionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    county: str = "Sarasota"
    case_number: str | None = None
    parcel_id_raw: str | None = None
    parcel_id_normalized: str | None = None
    auction_date: date | None = None
    auction_status: AuctionStatus = "unknown"
    opening_bid_cents: int | None = None
    appraiser_assessment_cents: int | None = None
    detail_url: str | None = None
    notice_url: str | None = None
    tax_deed_record_url: str | None = None
    source_fixture_path: str | None = None
    parse_confidence: float = Field(ge=0.0, le=1.0)
    missing_fields: tuple[str, ...] = ()
    parse_warnings: tuple[str, ...] = ()


class QuarantinedAuctionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_fixture_path: str
    parse_confidence: float = Field(ge=0.0, le=1.0)
    missing_fields: tuple[str, ...]
    parse_warnings: tuple[str, ...]
    extracted_record: NormalizedAuctionRecord
    quarantine_reason: str


class FixtureReplayResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: tuple[NormalizedAuctionRecord, ...]
    quarantined_records: tuple[QuarantinedAuctionRecord, ...]
