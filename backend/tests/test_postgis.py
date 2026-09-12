"""PostGIS tests. Skipped unless DATABASE_URL is PostgreSQL."""
import pytest
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base, ensure_schema, is_postgres
from app.core.spatial import distance_meters_postgis, nearest_zone_id
from app.services.demo_seed import seed_base_entities

pytestmark = pytest.mark.skipif(not is_postgres(), reason="requires PostgreSQL + PostGIS")


def setup_function():
    Base.metadata.drop_all(bind=engine)
    ensure_schema()


def test_postgis_extension():
    with engine.connect() as conn:
        assert conn.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')")).scalar()


def test_spatial_point_storage_and_nearest():
    db = SessionLocal()
    try:
        seed_base_entities(db)
        row = db.execute(text("SELECT ST_X(location), ST_Y(location) FROM zones WHERE id='ZONE_A'")).first()
        assert row is not None
        assert abs(row[0] - 72.8777) < 0.001
        assert abs(row[1] - 19.0760) < 0.001
        # ZONE_A is the coastal point; a nearby lon/lat should resolve to ZONE_A or a neighbor, not empty.
        zid = nearest_zone_id(db, 19.0760, 72.8777)
        assert zid == "ZONE_A"
    finally:
        db.close()


def test_spatial_distance_query():
    db = SessionLocal()
    try:
        meters = distance_meters_postgis(db, 72.8777, 19.0760, 72.8777, 19.0760)
        assert meters < 1
        meters2 = distance_meters_postgis(db, 72.8777, 19.0760, 72.8697, 19.1136)
        assert meters2 > 1000
    finally:
        db.close()


def test_migration_indexes_exist():
    with engine.connect() as conn:
        names = [r[0] for r in conn.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename IN ('incidents','resources','allocations','coordination_tasks','zones')"
        ))]
        assert "ix_incidents_timestamp" in names
        assert "ix_resources_status" in names
        assert "ix_zones_location" in names
