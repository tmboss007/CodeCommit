from app.core.database import SessionLocal, engine, Base
from app.core.events import AGENT_SSE, event_bus, events_from_audit
from app.models import Allocation, Incident
from app.services.incident_graph import (
    after_replanning,
    build_incident_graph,
    coordination_node,
    duplicate_node,
    needs_node,
    optimization_node,
    priority_node,
    replanning_node,
    situation_node,
)
from app.services.orchestration import OrchestrationService


def _db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def test_graph_initialization():
    graph = build_incident_graph()
    assert graph is not None
    assert callable(graph.invoke)


def test_situation_node():
    db = _db()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        out = situation_node({
            "orchestrator": orch,
            "report_text": "Flood in Zone A. 800 people affected.",
            "source": "test",
            "zone_id": "ZONE_A",
            "correlation_id": "corr_sit",
            "errors": [],
        })
        assert out["structured_incident"]["zone_id"] == "ZONE_A"
        assert not out.get("errors")
    finally:
        db.close()


def test_duplicate_node():
    db = _db()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        structured = orch.situation_step("Flood Zone A", "test", "ZONE_A", "corr_dup")
        out = duplicate_node({
            "orchestrator": orch,
            "report_text": "Flood Zone A",
            "structured_incident": structured,
            "correlation_id": "corr_dup",
            "errors": [],
        })
        assert "is_duplicate" in out["duplicate_result"]
    finally:
        db.close()


def test_needs_node():
    db = _db()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        structured = orch.situation_step("Flood Zone B 1200 people", "test", "ZONE_B", "corr_need")
        dup = orch.duplicate_step("Flood Zone B 1200 people", structured, "corr_need")
        out = needs_node({
            "orchestrator": orch,
            "report_text": "Flood Zone B 1200 people",
            "source": "test",
            "structured_incident": structured,
            "duplicate_result": dup,
            "correlation_id": "corr_need",
            "errors": [],
        })
        assert out["incident_id"]
        assert out["needs_created"] > 0
        assert db.query(Incident).filter(Incident.id == out["incident_id"]).first()
    finally:
        db.close()


def test_priority_node():
    db = _db()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()
        structured = orch.situation_step("Landslide Zone D", "test", "ZONE_D", "corr_pri")
        dup = orch.duplicate_step("Landslide Zone D", structured, "corr_pri")
        incident_id, needs = orch.needs_step("Landslide Zone D", "test", structured, dup, "corr_pri")
        out = priority_node({
            "orchestrator": orch,
            "incident_id": incident_id,
            "correlation_id": "corr_pri",
            "errors": [],
        })
        assert out["zone_priority"] is not None
        assert out["zone_priority"] > 0
    finally:
        db.close()


def test_replan_conditional_branch():
    assert after_replanning({"replan_required": False, "auto_replan": True, "errors": []}) == "end"
    assert after_replanning({"replan_required": True, "auto_replan": False, "errors": []}) == "end"
    assert after_replanning({"replan_required": True, "auto_replan": True, "errors": []}) == "optimize"
    assert after_replanning({"replan_required": True, "auto_replan": True, "errors": ["boom"]}) == "end"


def test_optimization_and_coordination_branch():
    db = _db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        orch.approve_plan(loaded["plan"]["plan_id"])
        packed = optimization_node({
            "orchestrator": orch,
            "correlation_id": "corr_opt",
            "replanning_reason": "test replan",
            "old_snapshot": orch._current_snapshot(),
            "errors": [],
        })
        assert packed["optimization_result"]["allocations"]
        assert db.query(Allocation).filter(Allocation.status == "pending").count() > 0
        coord = coordination_node({
            "orchestrator": orch,
            "optimization_result": packed["optimization_result"],
            "errors": [],
        })
        assert coord["current_plan"]["plan_id"]
        assert coord["coordination_tasks"]
        assert coord["current_plan"]["delta"] is not None
    finally:
        db.close()


def test_graph_error_handling():
    db = _db()
    try:
        orch = OrchestrationService(db)
        orch.reset_world()

        def boom(*_a, **_k):
            raise RuntimeError("situation down")

        orch.situation_agent.analyze_report = boom
        result = orch.process_incident_report("anything", "test", zone_id="ZONE_A", auto_replan=True)
        assert result["error"] == "pipeline_failed"
        assert result["plan"] is None
        assert any("situation" in d for d in result["details"])
        assert db.query(Incident).count() == 0
        assert db.query(Allocation).count() == 0
    finally:
        db.close()


def test_end_to_end_graph_execution():
    db = _db()
    received = []
    unsub = event_bus.subscribe_sync(lambda e: received.append(e))
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        assert loaded["plan"]["plan_id"]
        assert all(r.get("plan") is None for r in loaded["reports"])
        approved = orch.approve_plan(loaded["plan"]["plan_id"])
        assert approved["status"] == "approved"
        urgent = orch.inject_urgent_zone_a()
        assert urgent["replanning_required"] is True
        assert urgent["plan"]["plan_id"]
        types = {e["event_type"] for e in received}
        assert "agent.situation.completed" in types
        assert "agent.needs.completed" in types
        assert "agent.priority.completed" in types
        assert orch.approve_plan(urgent["plan"]["plan_id"])["status"] == "approved"
    finally:
        unsub()
        db.close()


def test_agent_sse_from_same_audit_row():
    payloads = events_from_audit(
        audit_id="evt_x",
        audit_type="REPLAN_TRIGGERED",
        description="replan",
        correlation_id="c1",
    )
    types = {e["event_type"] for e in payloads}
    assert "plan.replanned" in types
    assert AGENT_SSE["REPLAN_TRIGGERED"] in types
    assert "audit.created" in types
