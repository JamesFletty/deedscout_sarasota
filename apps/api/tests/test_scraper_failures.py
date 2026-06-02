from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import core  # noqa: F401
from app.models.core import ScraperFailure


def test_failed_scraper_attempt_can_be_stored() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        failure = ScraperFailure(
            source_url="https://www.sarasotaclerk.com/Home-and-Property/Tax-Deeds/Tax-Deed-Auctions",
            error_message="blocked or unavailable",
            retry_count=2,
        )
        session.add(failure)
        session.commit()

        stored = session.scalar(select(ScraperFailure).where(ScraperFailure.source_url == failure.source_url))

    assert stored is not None
    assert stored.retry_count == 2
