from app.core.database import SessionLocal, engine, Base
from app.services.orchestration import OrchestrationService
from app.models import Allocation, AuditEvent, CoordinationTask, Resource, AppState


def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def test_approve_revised_plan():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        first_id = loaded["plan"]["plan_id"]
        first = orch.approve_plan(first_id)
        assert first["status"] == "approved"

        urgent = orch.inject_urgent_zone_a()
        revised_id = urgent["plan"]["plan_id"]
        assert revised_id != first_id
        card = orch.revise_plan_card(revised_id)
        assert card["pending"] is True

        result = orch.approve_plan(revised_id)
        assert result["status"] == "approved"
        assert result["allocations_approved"] > 0
        assert result["tasks_approved"] > 0

        remaining = db.query(Allocation).filter(Allocation.plan_id == revised_id, Allocation.status == "pending").count()
        assert remaining == 0
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.last_plan_status == "approved"
        assert state.active_plan_id == revised_id
        assert orch.revise_plan_card(revised_id)["pending"] is False
    finally:
        db.close()


def test_reject_revised_plan():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        first_id = loaded["plan"]["plan_id"]
        orch.approve_plan(first_id)
        resource_before = {
            r.id: (r.status, r.current_zone_id)
            for r in db.query(Resource).all()
        }

        urgent = orch.inject_urgent_zone_a()
        revised_id = urgent["plan"]["plan_id"]
        rejected = orch.reject_plan(revised_id)
        assert rejected["status"] == "rejected"
        assert rejected["active_plan_id"] == first_id

        pending = db.query(Allocation).filter(Allocation.plan_id == revised_id, Allocation.status == "pending").count()
        assert pending == 0
        rejected_allocs = db.query(Allocation).filter(Allocation.plan_id == revised_id, Allocation.status == "rejected").count()
        assert rejected_allocs > 0

        for resource in db.query(Resource).all():
            assert (resource.status, resource.current_zone_id) == resource_before[resource.id]

        first_still_active = db.query(Allocation).filter(
            Allocation.plan_id == first_id, Allocation.status == "approved"
        ).count()
        assert first_still_active > 0
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.active_plan_id == first_id
        types = {e.event_type for e in db.query(AuditEvent).all()}
        assert "PLAN_REJECTED" in types
    finally:
        db.close()


def test_approval_changes_allocation():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        orch.approve_plan(plan_id)
        approved = db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "approved").count()
        pending = db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "pending").count()
        assert approved > 0
        assert pending == 0
    finally:
        db.close()


def test_approval_changes_resource_state():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        orch.approve_plan(plan_id)
        alloc = db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "approved").first()
        resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
        assert resource.status in ("en_route", "reserved", "deployed")
        assert resource.current_zone_id == alloc.zone_id
    finally:
        db.close()


def test_approval_changes_coordination_tasks():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        pending_before = db.query(CoordinationTask).filter(CoordinationTask.status == "pending").count()
        assert pending_before > 0
        orch.approve_plan(plan_id)
        pending_after = db.query(CoordinationTask).filter(CoordinationTask.status == "pending").count()
        approved = db.query(CoordinationTask).filter(CoordinationTask.status == "approved").count()
        assert pending_after == 0
        assert approved == pending_before
    finally:
        db.close()


def test_approval_creates_audit_events():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        orch.approve_plan(plan_id)
        events = db.query(AuditEvent).all()
        types = {e.event_type for e in events}
        assert "PLAN_APPROVED" in types
        assert "APPROVAL_GRANTED" in types
        parent = [e for e in events if e.event_type == "PLAN_APPROVED"]
        assert len(parent) == 1
        children = [e for e in events if e.event_type == "APPROVAL_GRANTED"]
        assert len(children) >= 1
    finally:
        db.close()


def test_failed_validation_causes_zero_partial_changes():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        alloc = db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "pending").first()
        resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
        resource.status = "unavailable"
        db.commit()

        result = orch.approve_plan(plan_id)
        assert result["error"] == "validation_failed"

        still_pending = db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "pending").count()
        approved = db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "approved").count()
        assert still_pending > 0
        assert approved == 0
        resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
        assert resource.status == "unavailable"
        types = {e.event_type for e in db.query(AuditEvent).all()}
        assert "PLAN_APPROVED" not in types
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.last_plan_status == "pending"
    finally:
        db.close()


def test_already_approved_plan_cannot_be_approved_twice():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        first = orch.approve_plan(plan_id)
        assert first["status"] == "approved"
        second = orch.approve_plan(plan_id)
        assert second["error"] == "already_approved"
        assert second["status_code"] == 409
        parents = db.query(AuditEvent).filter(AuditEvent.event_type == "PLAN_APPROVED").count()
        assert parents == 1
    finally:
        db.close()
