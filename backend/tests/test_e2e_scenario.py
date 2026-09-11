from app.core.database import SessionLocal, engine, Base
from app.services.orchestration import OrchestrationService
from app.models import Allocation, AuditEvent, CoordinationTask, Resource, AppState


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

        initial_id = loaded["plan"]["plan_id"]
        initial = orch.approve_plan(initial_id)
        assert initial["status"] == "approved"
        assert db.query(CoordinationTask).filter(CoordinationTask.status == "pending").count() == 0

        urgent = orch.inject_urgent_zone_a()
        assert urgent["zone_id"] == "ZONE_A"
        assert urgent["replanning_required"] is True
        assert urgent["plan"] is not None
        assert urgent["plan"]["delta"] is not None
        if before_priority is not None:
            assert urgent["zone_priority_updated"] >= before_priority

        revised_id = urgent["plan"]["plan_id"]
        assert revised_id != initial_id
        card = orch.revise_plan_card(revised_id)
        assert card["pending"] is True
        assert card["review"]["total_movements"] >= 1

        approved = orch.approve_plan(revised_id)
        assert approved["status"] == "approved"
        assert db.query(Allocation).filter(Allocation.plan_id == revised_id, Allocation.status == "pending").count() == 0
        assert db.query(CoordinationTask).filter(CoordinationTask.status == "pending").count() == 0
        assert db.query(Resource).filter(Resource.status.in_(["en_route", "reserved", "deployed"])).count() > 0

        events = db.query(AuditEvent).all()
        types = {e.event_type for e in events}
        assert "REPLAN_TRIGGERED" in types or "ALLOCATION_CHANGED" in types
        assert "PLAN_APPROVED" in types
        assert "APPROVAL_GRANTED" in types
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.active_plan_id == revised_id
        assert orch.revise_plan_card()["pending"] is False
    finally:
        db.close()
