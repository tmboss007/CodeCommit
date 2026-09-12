"""Seed canonical demo entities (5 zones, 5 agencies, 15 resources)."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, ensure_schema
from app.services.demo_seed import seed_base_entities, ZONES, AGENCIES, RESOURCES


def seed_data():
    ensure_schema()
    db = SessionLocal()
    try:
        seed_base_entities(db)
        print("Demo data seeded")
        print(f"   - {len(ZONES)} zones")
        print(f"   - {len(AGENCIES)} agencies")
        print(f"   - {len(RESOURCES)} resources")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
