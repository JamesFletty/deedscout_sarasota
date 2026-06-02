from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import core  # noqa: F401
from app.models.core import SourceSnapshot


def test_source_snapshot_can_store_page_structure_hash() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        snapshot = SourceSnapshot(
            source_url="https://example.test/detail",
            content_hash="a" * 64,
            page_structure_hash="b" * 64,
            parser_version="parser-v1",
            scraped_at=datetime.now(UTC),
        )
        session.add(snapshot)
        session.commit()

        stored = session.scalar(select(SourceSnapshot).where(SourceSnapshot.content_hash == "a" * 64))

    assert stored is not None
    assert stored.page_structure_hash == "b" * 64
