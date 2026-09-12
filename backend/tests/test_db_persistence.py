"""Persistence tests that run on SQLite or PostgreSQL."""
from datetime import datetime
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base, ensure_schema, is_postgres
from app.models import Incident, Resource, Allocation, Plan, AuditEvent, Zone, Agency


def setup_function():
    Base.metadata.drop_all(bind=engine)
    ensure_schema()


def test_database_connection():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def test_incident_resource_allocation_plan_audit_persist():
    db = SessionLocal()
    try:
        db.add(Zone(id="ZONE_A", name="A", latitude=19.0, longitude=72.8, population=1, vulnerable_population=0))
        db.add(Agency(id="NDRF", name="NDRF", type="rescue", capabilities=[]))
        db.commit()
        db.add(Resource(id="R01", name="Team", type="rescue_team", agency_id="NDRF", latitude=19.0, longitude=72.8, quantity=1, unit="team", status="available"))
        db.add(Incident(id="inc_1", zone_id="ZONE_A", source="field", report_text="flood", status="active", timestamp=datetime.utcnow()))
        db.add(Plan(id="plan_1", status="pending_approval", trigger="manual"))
        db.add(Allocation(id="alloc_1", resource_id="R01", zone_id="ZONE_A", quantity=1, status="pending", plan_id="plan_1"))
        db.add(AuditEvent(id="aud_1", event_type="TEST", description="persisted", actor="system"))
        db.commit()

        assert db.query(Incident).filter_by(id="inc_1").one().zone_id == "ZONE_A"
        assert db.query(Resource).filter_by(id="R01").one().status == "available"
        assert db.query(Allocation).filter_by(id="alloc_1").one().plan_id == "plan_1"
        assert db.query(Plan).filter_by(id="plan_1").one().status == "pending_approval"
        assert db.query(AuditEvent).filter_by(id="aud_1").one().event_type == "TEST"
    finally:
        db.close()


def test_postgres_flag_matches_url():
    assert is_postgres() == str(engine.url).startswith("postgresql")
