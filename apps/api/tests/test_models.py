from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import core  # noqa: F401
from app.models.core import AuctionRecord
from app.models.factories import create_sample_batch_with_records


def test_sample_batch_and_records_can_be_created_and_queried() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        batch = create_sample_batch_with_records(session)
        records = session.scalars(select(AuctionRecord).where(AuctionRecord.batch_id == batch.id)).all()

    assert len(records) == 2
    assert {record.parcel_id_normalized for record in records} == {"0123456789", "9876543210"}
