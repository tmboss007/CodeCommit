from app.core.database import SessionLocal, engine, Base
from app.services.orchestration import OrchestrationService
from app.models import CoordinationTask, Allocation, Resource, AuditEvent


def test_approval_updates_resource_reject_does_not():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        tasks = loaded["plan"]["coordination_tasks"]
        assert len(tasks) >= 2
        first = orch.approve_task(tasks[0]["id"])
        assert first["status"] == "approved"
        task = db.query(CoordinationTask).filter(CoordinationTask.id == tasks[0]["id"]).first()
        assert task.status == "approved"
        alloc = db.query(Allocation).filter(Allocation.id == task.allocation_id).first()
        assert alloc.status == "approved"
        resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
        assert resource.status in ("en_route", "reserved", "deployed")
        assert resource.current_zone_id == alloc.zone_id

        rejected = orch.reject_task(tasks[1]["id"])
        assert rejected["status"] == "rejected"
        task2 = db.query(CoordinationTask).filter(CoordinationTask.id == tasks[1]["id"]).first()
        assert task2.status == "rejected"
        alloc2 = db.query(Allocation).filter(Allocation.id == task2.allocation_id).first()
        assert alloc2.status == "rejected"
        resource2 = db.query(Resource).filter(Resource.id == alloc2.resource_id).first()
        assert resource2.status == "available"

        types = {e.event_type for e in db.query(AuditEvent).all()}
        assert "APPROVAL_GRANTED" in types
        assert "APPROVAL_REJECTED" in types
    finally:
        db.close()


def test_reset_scenario_seeds_inventory_without_incidents():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        from app.models import Incident, Resource, Zone
        assert db.query(Zone).count() == 5
        assert db.query(Resource).count() >= 12
        assert db.query(Incident).count() == 0
    finally:
        db.close()
