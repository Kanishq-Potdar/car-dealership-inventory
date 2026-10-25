"""Insert labeled sample catalogue rows without replacing any existing listing."""
import csv
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Vehicle
from app.vehicles import VehicleRequest


def load_catalogue():
    path = Path(__file__).resolve().parents[1] / "data" / "sample_vehicles.csv"
    rows = []
    keys = set()
    with path.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            key = "sample-v1:" + row.pop("sample_id")
            if key in keys or len(key) > 100:
                raise ValueError("Invalid or duplicate sample catalogue key")
            keys.add(key)
            row["year"] = int(row["year"])
            row["quantity"] = int(row["quantity"])
            rows.append({**VehicleRequest.model_validate(row).model_dump(), "sample_key": key})
    return rows


def seed_catalogue(session):
    rows = load_catalogue()
    try:
        inserted = session.scalars(insert(Vehicle).values(rows).on_conflict_do_nothing(
            index_elements=[Vehicle.sample_key]
        ).returning(Vehicle.id)).all()
        session.commit()
        return len(inserted)
    except Exception:
        session.rollback()
        raise


def main():
    engine = get_engine()
    try:
        with Session(engine) as session:
            count = seed_catalogue(session)
        print(f"Inserted {count} SAMPLE vehicles. Existing listings were not updated.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
