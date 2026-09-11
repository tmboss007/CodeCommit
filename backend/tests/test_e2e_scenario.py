from app.core.database import SessionLocal, engine, Base
from app.services.orchestration import OrchestrationService


def test_closed_loop_demo_scenario():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        assert loaded["plan"]["plan_id"]
        assert len(loaded["reports"]) == 5
        assert len(loaded["plan"]["allocations"]) > 0

        before_priority = None
        for report in loaded["reports"]:
            if report["zone_id"] == "ZONE_A":
                before_priority = report["zone_priority_updated"]

        urgent = orch.inject_urgent_zone_a()
        assert urgent["zone_id"] == "ZONE_A"
        assert urgent["replanning_required"] is True
        assert urgent["plan"] is not None
        assert urgent["plan"]["delta"] is not None
        if before_priority is not None:
            assert urgent["zone_priority_updated"] >= before_priority

        tasks = urgent["plan"]["coordination_tasks"]
        assert len(tasks) > 0
        approved = orch.approve_task(tasks[0]["id"])
        assert approved["status"] == "approved"

        from app.models import CoordinationTask, Allocation, AuditEvent
        task = db.query(CoordinationTask).filter(CoordinationTask.id == tasks[0]["id"]).first()
        assert task.status == "approved"
        if task.allocation_id:
            alloc = db.query(Allocation).filter(Allocation.id == task.allocation_id).first()
            assert alloc.status == "approved"

        events = db.query(AuditEvent).all()
        types = {e.event_type for e in events}
        assert "REPLAN_TRIGGERED" in types or "ALLOCATION_CHANGED" in types
        assert "APPROVAL_GRANTED" in types
    finally:
        db.close()
