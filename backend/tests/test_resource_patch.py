from app.core.database import SessionLocal, engine, Base
from app.services.orchestration import OrchestrationService
from app.models import Resource, AuditEvent, AppState
from app.api.ops import snapshot


def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def test_resource_patch_updates_state_and_audit():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        orch.approve_plan(loaded["plan"]["plan_id"])
        resource = db.query(Resource).filter(Resource.status.in_(["en_route", "reserved", "deployed"])).first()
        assert resource is not None
        before = resource.status
        deployed_before = snapshot(db)["metrics"]["deployed_resources"]
        result = orch.update_resource(
            resource.id,
            {"status": "available", "current_zone_id": "ZONE_B", "eta_minutes": None},
            reason="Manual inventory correction",
        )
        assert result["status"] == "available"
        assert result["current_zone_id"] == "ZONE_B"
        resource = db.query(Resource).filter(Resource.id == resource.id).first()
        assert resource.status == "available"
        assert resource.current_zone_id == "ZONE_B"
        events = db.query(AuditEvent).filter(AuditEvent.event_type == "RESOURCE_STATE_CHANGED").all()
        manual = [e for e in events if e.actor == "operator" and e.reason == "Manual inventory correction"]
        assert len(manual) >= 1
        assert manual[-1].previous_state["status"] == before
        assert manual[-1].new_state["status"] == "available"
        assert manual[-1].correlation_id
        snap = snapshot(db)
        assert any(r["id"] == resource.id and r["status"] == "available" for r in snap["resources"])
        assert snap["metrics"]["deployed_resources"] < deployed_before
    finally:
        db.close()


def test_invalid_resource_patch_rejected():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        bad_status = orch.update_resource("R01", {"status": "flying"})
        assert bad_status["error"] == "invalid_status"
        bad_zone = orch.update_resource("R01", {"current_zone_id": "ZONE_Z"})
        assert bad_zone["error"] == "invalid_zone"
        missing = orch.update_resource("NOPE", {"status": "available"})
        assert missing["error"] == "not_found"
        resource = db.query(Resource).filter(Resource.id == "R01").first()
        assert resource.status == "available"
        assert db.query(AuditEvent).filter(AuditEvent.event_type == "RESOURCE_STATE_CHANGED", AuditEvent.actor == "operator").count() == 0
    finally:
        db.close()


def test_unavailable_resource_cannot_be_in_new_plan():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        alloc = loaded["plan"]["allocations"][0]
        orch.update_resource(alloc["resource_id"], {"status": "unavailable"})
        result = orch.approve_plan(loaded["plan"]["plan_id"])
        assert result["error"] == "validation_failed"
        assert db.query(AppState).filter(AppState.id == "singleton").first().last_plan_status == "pending"
    finally:
        db.close()
