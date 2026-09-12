import threading
import time
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.core.events import build_event, event_bus, events_from_audit, format_sse, map_audit_type
from app.main import app
from app.models import Resource
from app.services.orchestration import OrchestrationService


def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def test_event_serialization():
    event = build_event(
        "plan.approved",
        "Revised response plan approved",
        correlation_id="corr_test",
        actor="operator",
        extra={"plan_id": "plan_1"},
    )
    body = format_sse(event)
    assert body.startswith("event: plan.approved\n")
    assert '"event_type":"plan.approved"' in body
    assert '"correlation_id":"corr_test"' in body
    assert '"plan_id":"plan_1"' in body
    assert body.endswith("\n\n")


def test_audit_mapping_and_publication():
    received = []
    unsub = event_bus.subscribe_sync(lambda e: received.append(e))
    try:
        assert map_audit_type("PLAN_APPROVED") == "plan.approved"
        payloads = events_from_audit(
            audit_id="evt_1",
            audit_type="PLAN_APPROVED",
            description="Plan approved",
            actor="operator",
            correlation_id="plan_x",
            new_state={"plan_id": "plan_x"},
        )
        for item in payloads:
            event_bus.publish(item)
        types = {e["event_type"] for e in received}
        assert "plan.approved" in types
        assert "audit.created" in types
        assert all("timestamp" in e and "event_id" in e for e in received)
    finally:
        unsub()


def test_sse_endpoint_heartbeat_and_disconnect():
    event_bus.reset()
    q = event_bus.subscribe()
    assert event_bus.subscriber_count() == 1
    event_bus.unsubscribe(q)
    assert event_bus.subscriber_count() == 0

    client = TestClient(app)
    with client.stream("GET", "/api/events/stream?max_events=1") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        text = "".join(response.iter_text())
        assert "event: heartbeat" in text
        assert '"event_type":"heartbeat"' in text
    time.sleep(0.05)
    assert event_bus.subscriber_count() == 0


def test_approval_resource_and_replan_events():
    event_bus.reset()
    received = []
    unsub = event_bus.subscribe_sync(lambda e: received.append(e))
    db = _fresh_db()
    try:
        orch = OrchestrationService(db)
        loaded = orch.load_demo()
        plan_id = loaded["plan"]["plan_id"]
        approved = orch.approve_plan(plan_id)
        assert approved["status"] == "approved"
        types = {e["event_type"] for e in received}
        assert "plan.approved" in types
        assert "scenario.updated" in types

        received.clear()
        resource = db.query(Resource).first()
        patched = orch.update_resource(
            resource.id,
            {"status": "available"},
            actor="operator",
            reason="SSE test",
        )
        assert patched.get("id") == resource.id
        types = {e["event_type"] for e in received}
        assert "resource.updated" in types
        assert "audit.created" in types

        received.clear()
        urgent = orch.inject_urgent_zone_a()
        types = {e["event_type"] for e in received}
        assert "plan.replanned" in types or urgent.get("plan") is not None
        assert "incident.created" in types
        if urgent.get("plan"):
            assert "plan.created" in types or "allocation.changed" in types
        assert any(e["event_type"] == "scenario.updated" and "INJECT" in e["summary"] for e in received)
    finally:
        unsub()
        db.close()


def test_sse_backoff_contract():
    delays = [1000, 2000, 4000, 8000, 15000]
    def nxt(failed):
        return delays[min(max(failed - 1, 0), len(delays) - 1)]
    assert [nxt(i) for i in range(1, 7)] == [1000, 2000, 4000, 8000, 15000, 15000]


def test_close_all_unblocks_subscribers():
    event_bus.reset()
    q = event_bus.subscribe()
    assert event_bus.subscriber_count() == 1
    event_bus.close_all()
    assert event_bus.subscriber_count() == 0
    assert q.get_nowait()["event_type"] == "_shutdown"


def test_two_sse_streams_then_cleanup():
    event_bus.reset()
    q1 = event_bus.subscribe()
    q2 = event_bus.subscribe()
    assert event_bus.subscriber_count() == 2
    client = TestClient(app)
    with client.stream("GET", "/api/events/stream?max_events=1") as response:
        assert response.status_code == 200
        text = "".join(response.iter_text())
        assert "event: heartbeat" in text
    event_bus.unsubscribe(q1)
    event_bus.unsubscribe(q2)
    time.sleep(0.05)
    assert event_bus.subscriber_count() == 0


def test_sse_event_delivery_and_heartbeat():
    event_bus.reset()
    client = TestClient(app)

    def later():
        time.sleep(0.15)
        event_bus.publish(build_event("plan.approved", "delivered"))

    thread = threading.Thread(target=later, daemon=True)
    thread.start()
    with client.stream("GET", "/api/events/stream?heartbeat_ms=400&max_events=3") as response:
        text = "".join(response.iter_text())
    thread.join(timeout=2)
    assert "event: heartbeat" in text
    assert "event: plan.approved" in text
    assert event_bus.subscriber_count() == 0


def test_shutdown_closes_live_stream():
    event_bus.reset()
    q = event_bus.subscribe()
    event_bus.close_all()
    assert event_bus.subscriber_count() == 0
    assert q.get_nowait()["event_type"] == "_shutdown"
    client = TestClient(app)
    with client.stream("GET", "/api/events/stream?max_events=1") as response:
        text = "".join(response.iter_text())
    assert "event: heartbeat" in text
    time.sleep(0.05)
    assert event_bus.subscriber_count() == 0


def test_sse_disabled_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "SSE_ENABLED", "false")
    client = TestClient(app)
    response = client.get("/api/events/stream")
    assert response.status_code == 503

