"""In-process event bus for operational SSE.

Publishers are sync SQLAlchemy services. The SSE endpoint subscribes with
asyncio queues. Replace this module with Redis pub/sub later without changing
orchestration call sites.
"""
from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


AUDIT_TO_SSE = {
    "INCIDENT_CREATED": "incident.created",
    "INCIDENT_ANALYZED": "incident.updated",
    "PRIORITY_CHANGED": "priority.changed",
    "NEEDS_UPDATED": "needs.updated",
    "DUPLICATE_DETECTED": "duplicate.detected",
    "ALLOCATION_CREATED": "plan.created",
    "ALLOCATION_CHANGED": "allocation.changed",
    "REPLAN_TRIGGERED": "plan.replanned",
    "PLAN_APPROVED": "plan.approved",
    "PLAN_REJECTED": "plan.rejected",
    "RESOURCE_STATE_CHANGED": "resource.updated",
    "APPROVAL_GRANTED": "coordination.updated",
    "APPROVAL_REJECTED": "coordination.updated",
}

AGENT_SSE = {
    "INCIDENT_CREATED": "agent.situation.completed",
    "INCIDENT_ANALYZED": "agent.duplicate.completed",
    "DUPLICATE_DETECTED": "agent.duplicate.completed",
    "NEEDS_UPDATED": "agent.needs.completed",
    "PRIORITY_CHANGED": "agent.priority.completed",
    "REPLAN_TRIGGERED": "agent.replanning.triggered",
    "ALLOCATION_CREATED": "agent.optimization.completed",
    "ALLOCATION_CHANGED": "agent.coordination.completed",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def map_audit_type(audit_type: str) -> Optional[str]:
    return AUDIT_TO_SSE.get(audit_type)


def build_event(
    event_type: str,
    summary: str,
    *,
    event_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    actor: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "event_id": event_id or str(uuid.uuid4()),
        "event_type": event_type,
        "timestamp": utc_now_iso(),
        "correlation_id": correlation_id,
        "actor": actor or "system",
        "summary": summary,
    }
    if extra:
        for key, value in extra.items():
            if key not in payload and value is not None:
                payload[key] = value
    return payload


def events_from_audit(
    *,
    audit_id: str,
    audit_type: str,
    description: str,
    actor: Optional[str] = None,
    agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
    new_state: Optional[Dict[str, Any]] = None,
    previous_state: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    extra: Dict[str, Any] = {"audit_id": audit_id, "audit_type": audit_type}
    if isinstance(new_state, dict) and new_state.get("plan_id"):
        extra["plan_id"] = new_state["plan_id"]
    who = actor or agent or "system"
    mapped = map_audit_type(audit_type)
    events: List[Dict[str, Any]] = []
    if mapped:
        events.append(
            build_event(
                mapped,
                description,
                event_id=str(uuid.uuid4()),
                correlation_id=correlation_id,
                actor=who,
                extra=extra,
            )
        )
    agent_mapped = AGENT_SSE.get(audit_type)
    if agent_mapped:
        events.append(
            build_event(
                agent_mapped,
                description,
                event_id=str(uuid.uuid4()),
                correlation_id=correlation_id,
                actor=who,
                extra=extra,
            )
        )
    events.append(
        build_event(
            "audit.created",
            description,
            event_id=audit_id,
            correlation_id=correlation_id,
            actor=who,
            extra=extra,
        )
    )
    return events


def format_sse(event: Dict[str, Any]) -> str:
    event_type = event.get("event_type") or "message"
    data = json.dumps(event, default=str, separators=(",", ":"))
    return f"event: {event_type}\ndata: {data}\n\n"


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: List[asyncio.Queue] = []
        self._sync_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._queues)

    def reset(self) -> None:
        self.close_all()
        with self._lock:
            self._sync_listeners.clear()

    def close_all(self) -> None:
        """Unblock SSE generators so shutdown does not wait on dead clients."""
        with self._lock:
            queues = list(self._queues)
            self._queues.clear()
            self._loop = None
        for queue in queues:
            try:
                while True:
                    queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait({"event_type": "_shutdown", "summary": "bus closed"})
            except Exception:
                pass

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        with self._lock:
            self._queues.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            if queue in self._queues:
                self._queues.remove(queue)

    def subscribe_sync(self, callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            self._sync_listeners.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._sync_listeners:
                    self._sync_listeners.remove(callback)

        return unsubscribe

    def _put(self, queue: asyncio.Queue, event: Dict[str, Any]) -> None:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except Exception:
                pass
            try:
                queue.put_nowait(event)
            except Exception:
                pass

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            queues = list(self._queues)
            listeners = list(self._sync_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass
        loop = self._loop
        for queue in queues:
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._put, queue, event)
            else:
                self._put(queue, event)


event_bus = EventBus()
