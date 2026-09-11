from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models import Incident
from app.schemas import Incident as IncidentSchema
from app.services.orchestration import OrchestrationService

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


class IncidentCreate(BaseModel):
    report_text: str
    source: str = "operator"
    source_reference: Optional[str] = None
    zone_id: Optional[str] = None


@router.post("", response_model=dict)
@router.post("/", response_model=dict, include_in_schema=False)
def create_incident(incident: IncidentCreate, db: Session = Depends(get_db)):
    orchestrator = OrchestrationService(db)
    return orchestrator.process_incident_report(
        report_text=incident.report_text,
        source=incident.source,
        zone_id=incident.zone_id,
        auto_replan=True,
    )


@router.get("", response_model=List[IncidentSchema])
@router.get("/", response_model=List[IncidentSchema], include_in_schema=False)
def list_incidents(zone_id: str = None, status: str = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Incident)
    if zone_id:
        query = query.filter(Incident.zone_id == zone_id)
    if status:
        query = query.filter(Incident.status == status)
    return query.order_by(Incident.timestamp.desc()).limit(limit).all()


@router.get("/{incident_id}", response_model=IncidentSchema)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
