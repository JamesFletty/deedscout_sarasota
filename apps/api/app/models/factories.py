from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.core import AuctionBatch, AuctionRecord, utc_now


def create_sample_batch_with_records(session: Session) -> AuctionBatch:
    batch = AuctionBatch(
        county="Sarasota",
        source="sarasota_tax_deed_fixture",
        status="completed",
        started_at=utc_now(),
        records_found=2,
        records_valid=2,
    )
    session.add(batch)
    session.flush()
    session.add_all(
        [
            AuctionRecord(
                batch_id=batch.id,
                county="Sarasota",
                case_number="2026-TD-001",
                parcel_id_raw="0123-45-6789",
                parcel_id_normalized="0123456789",
                auction_date=date(2026, 7, 10),
                auction_status="scheduled",
                opening_bid_cents=1250000,
                appraiser_assessment_cents=5000000,
                parse_confidence=Decimal("0.9500"),
            ),
            AuctionRecord(
                batch_id=batch.id,
                county="Sarasota",
                case_number="2026-TD-002",
                parcel_id_raw="9876-54-3210",
                parcel_id_normalized="9876543210",
                auction_date=date(2026, 7, 10),
                auction_status="scheduled",
                opening_bid_cents=2500000,
                appraiser_assessment_cents=8000000,
                parse_confidence=Decimal("0.9000"),
            ),
        ]
    )
    session.commit()
    session.refresh(batch)
    return batch
