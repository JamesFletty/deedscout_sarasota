from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import core  # noqa: F401
from app.models.factories import create_sample_batch_with_records


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        batch = create_sample_batch_with_records(session)
        print(f"created sample batch {batch.id}")


if __name__ == "__main__":
    main()
