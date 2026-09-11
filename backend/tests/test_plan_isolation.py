from app.core.database import SessionLocal, engine, Base
from app.services.orchestration import OrchestrationService
from app.models import Allocation, CoordinationTask, Plan, AppState, Resource, AuditEvent
from app.api.ops import snapshot


def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def test_plan_a_becomes_active_then_b_supersedes_a():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_a = loaded["plan"]["plan_id"]
        assert loaded["plan"]["previous_plan_id"] is None
        first = orch.approve_plan(plan_a)
        assert first["status"] == "approved"
        assert first["active_plan_id"] == plan_a
        row = db.query(Plan).filter(Plan.id == plan_a).first()
        assert row.status == "active"
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.active_plan_id == plan_a

        urgent = orch.inject_urgent_zone_a()
        plan_b = urgent["plan"]["plan_id"]
        assert plan_b != plan_a
        assert urgent["plan"]["previous_plan_id"] == plan_a
        pending_b = db.query(Plan).filter(Plan.id == plan_b).first()
        assert pending_b.status == "pending_approval"
        assert pending_b.previous_plan_id == plan_a

        second = orch.approve_plan(plan_b)
        assert second["active_plan_id"] == plan_b
        assert second["previous_plan_id"] == plan_a
        db.refresh(row)
        db.refresh(pending_b)
        assert row.status == "superseded"
        assert pending_b.status == "active"
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.active_plan_id == plan_b

        active_tasks = orch.active_plan_tasks()
        assert len(active_tasks) > 0
        assert all(t.plan_id == plan_b for t in active_tasks)
        assert db.query(CoordinationTask).filter(CoordinationTask.plan_id == plan_a, CoordinationTask.status == "approved").count() == 0
        assert db.query(CoordinationTask).filter(CoordinationTask.plan_id == plan_a, CoordinationTask.status == "superseded").count() > 0
        assert db.query(Allocation).filter(Allocation.plan_id == plan_a).count() > 0

        snap = snapshot(db)
        assert snap["active_plan_id"] == plan_b
        history = [p for p in snap["plans"] if p["id"] == plan_a]
        assert history[0]["status"] == "superseded"

        db2 = SessionLocal()
        try:
            persisted = db2.query(AppState).filter(AppState.id == "singleton").first()
            assert persisted.active_plan_id == plan_b
        finally:
            db2.close()
    finally:
        db.close()


def test_reject_plan_preserves_active_plan():
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_a = loaded["plan"]["plan_id"]
        orch.approve_plan(plan_a)
        urgent = orch.inject_urgent_zone_a()
        plan_c = urgent["plan"]["plan_id"]
        rejected = orch.reject_plan(plan_c)
        assert rejected["active_plan_id"] == plan_a
        state = db.query(AppState).filter(AppState.id == "singleton").first()
        assert state.active_plan_id == plan_a
        assert db.query(Plan).filter(Plan.id == plan_a).first().status == "active"
        assert db.query(Plan).filter(Plan.id == plan_c).first().status == "rejected"
        assert len(orch.active_plan_tasks()) > 0
        assert all(t.plan_id == plan_a for t in orch.active_plan_tasks())
        assert db.query(Resource).filter(Resource.status.in_(["en_route", "reserved", "deployed"])).count() > 0
    finally:
        db.close()
