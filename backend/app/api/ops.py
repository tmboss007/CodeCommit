from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import (
    Zone, Incident, Resource, Allocation, CoordinationTask, AuditEvent, Need, Agency, AppState,
)
from app.providers.registry import data_sources_for_snapshot, get_disaster_provider, provider_status
from app.services.orchestration import OrchestrationService

router = APIRouter(prefix="/api", tags=["ops"])


@router.get("/allocations")
def list_allocations(status: str = None, db: Session = Depends(get_db)):
    q = db.query(Allocation)
    if status:
        q = q.filter(Allocation.status == status)
    else:
        q = q.filter(Allocation.status.in_(["pending", "approved"]))
    rows = q.order_by(Allocation.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "resource_id": a.resource_id,
            "zone_id": a.zone_id,
            "from_zone_id": a.from_zone_id,
            "quantity": a.quantity,
            "priority": a.priority,
            "eta_minutes": a.eta_minutes,
            "reason": a.reason,
            "status": a.status,
            "plan_id": a.plan_id,
            "created_at": a.created_at,
            "approved_at": a.approved_at,
            "approved_by": a.approved_by,
        }
        for a in rows
    ]


@router.get("/agencies")
def list_agencies(db: Session = Depends(get_db)):
    return [
        {"id": a.id, "name": a.name, "type": a.type, "contact": a.contact, "capabilities": a.capabilities}
        for a in db.query(Agency).all()
    ]


@router.get("/needs")
def list_needs(zone_id: str = None, db: Session = Depends(get_db)):
    q = db.query(Need)
    if zone_id:
        q = q.filter(Need.zone_id == zone_id)
    rows = q.all()
    return [
        {
            "id": n.id,
            "incident_id": n.incident_id,
            "zone_id": n.zone_id,
            "resource_type": n.resource_type,
            "quantity_required": n.quantity_required,
            "quantity_fulfilled": n.quantity_fulfilled,
            "quantity_remaining": n.quantity_remaining,
            "urgency": n.urgency,
            "unit": n.unit,
        }
        for n in rows
    ]


@router.get("/ops/snapshot")
def snapshot(db: Session = Depends(get_db)):
    state = db.query(AppState).filter(AppState.id == "singleton").first()
    zones = db.query(Zone).all()
    incidents = db.query(Incident).order_by(Incident.timestamp.desc()).limit(50).all()
    resources = db.query(Resource).all()
    allocations = db.query(Allocation).filter(Allocation.status.in_(["pending", "approved"])).all()
    tasks = db.query(CoordinationTask).order_by(CoordinationTask.assigned_at.desc()).all()
    audit = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(40).all()
    needs = db.query(Need).all()
    agencies = db.query(Agency).all()

    unmet_critical = 0.0
    required = sum(n.quantity_required or 0 for n in needs)
    remaining = sum((n.quantity_remaining if n.quantity_remaining is not None else n.quantity_required) or 0 for n in needs)
    coverage = 0.0
    if required:
        coverage = max(0, min(100, (1 - remaining / required) * 100))

    return {
        "data_mode": (state.data_mode if state else "SIMULATION"),
        "data_sources": data_sources_for_snapshot(),
        "last_plan_id": state.last_plan_id if state else None,
        "last_plan_status": state.last_plan_status if state else None,
        "active_plan_id": state.active_plan_id if state else None,
        "plans": OrchestrationService(db).list_plans() if state else [],
        "revised_plan": OrchestrationService(db).revise_plan_card() if state else None,
        "delta": state.last_delta if state else None,
        "unmet_demands": state.last_unmet if state else [],
        "explanation": state.last_explanation if state else None,
        "blocked_routes": state.blocked_routes if state else [],
        "metrics": {
            "active_incidents": len([i for i in incidents if i.status == "active"]),
            "critical_zones": len([z for z in zones if (z.priority_score or 0) >= 80]),
            "available_resources": len([r for r in resources if r.status == "available"]),
            "deployed_resources": len([r for r in resources if r.status in ("deployed", "en_route", "reserved")]),
            "unmet_critical_demand": remaining,
            "response_coverage": round(coverage, 1),
        },
        "zones": [
            {
                "id": z.id, "name": z.name, "latitude": z.latitude, "longitude": z.longitude,
                "population": z.population, "vulnerable_population": z.vulnerable_population,
                "severity": z.severity, "priority_score": z.priority_score,
                "priority_breakdown": z.priority_breakdown, "status": z.status,
            }
            for z in zones
        ],
        "incidents": [
            {
                "id": i.id, "zone_id": i.zone_id, "source": i.source, "report_text": i.report_text,
                "incident_type": i.incident_type, "timestamp": i.timestamp,
                "affected_population": i.affected_population, "vulnerable_population": i.vulnerable_population,
                "confidence": i.confidence, "status": i.status, "duplicate_status": i.duplicate_status,
                "duplicate_group_id": i.duplicate_group_id, "analysis_result": i.analysis_result,
            }
            for i in incidents
        ],
        "resources": [
            {
                "id": r.id, "name": r.name, "type": r.type, "agency_id": r.agency_id,
                "latitude": r.latitude, "longitude": r.longitude, "quantity": r.quantity, "unit": r.unit,
                "capacity": r.capacity, "capabilities": r.capabilities, "status": r.status,
                "current_zone_id": r.current_zone_id, "eta_minutes": r.eta_minutes,
            }
            for r in resources
        ],
        "allocations": [
            {
                "id": a.id, "resource_id": a.resource_id, "zone_id": a.zone_id, "from_zone_id": a.from_zone_id,
                "quantity": a.quantity, "priority": a.priority, "eta_minutes": a.eta_minutes,
                "reason": a.reason, "status": a.status, "plan_id": a.plan_id,
            }
            for a in allocations
        ],
        "tasks": [
            {
                "id": t.id, "agency_id": t.agency_id, "allocation_id": t.allocation_id,
                "plan_id": t.plan_id, "action": t.action, "status": t.status,
                "assigned_at": t.assigned_at, "approved_at": t.approved_at,
            }
            for t in tasks
        ],
        "needs": [
            {
                "id": n.id, "zone_id": n.zone_id, "resource_type": n.resource_type,
                "quantity_required": n.quantity_required, "quantity_fulfilled": n.quantity_fulfilled,
                "quantity_remaining": n.quantity_remaining, "unit": n.unit, "urgency": n.urgency,
            }
            for n in needs
        ],
        "agencies": [{"id": a.id, "name": a.name, "type": a.type} for a in agencies],
        "audit": [
            {
                "id": e.id, "timestamp": e.timestamp, "actor": e.actor, "agent": e.agent,
                "event_type": e.event_type, "description": e.description, "correlation_id": e.correlation_id,
                "previous_state": e.previous_state, "new_state": e.new_state, "reason": e.reason,
            }
            for e in audit
        ],
    }


@router.get("/providers/status")
def providers_status():
    return provider_status()


@router.post("/providers/ingest")
def ingest_provider_event(source: str = "gdacs", db: Session = Depends(get_db)):
    events = get_disaster_provider().fetch_events()
    if not events:
        return {"ingested": 0, "error": "no_events"}
    return OrchestrationService(db).ingest_external_event(events[0], auto_replan=True)
