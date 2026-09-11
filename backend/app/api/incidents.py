from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import Incident
from app.schemas import IncidentCreate, Incident as IncidentSchema
from app.services.orchestration import OrchestrationService
import uuid

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

@router.post("/", response_model=dict)
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db)):
    """Submit new incident report and process through agent pipeline."""
    orchestrator = OrchestrationService(db)

    result = orchestrator.process_incident_report(
        report_text=incident.report_text,
        source=incident.source,
        zone_id=None
    )

    return result

@router.get("/", response_model=List[IncidentSchema])
def list_incidents(
    zone_id: str = None,
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List incidents with optional filters."""
    query = db.query(Incident)

    if zone_id:
        query = query.filter(Incident.zone_id == zone_id)
    if status:
        query = query.filter(Incident.status == status)

    incidents = query.order_by(Incident.timestamp.desc()).limit(limit).all()
    return incidents

@router.get("/{incident_id}", response_model=IncidentSchema)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    """Get incident details."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
