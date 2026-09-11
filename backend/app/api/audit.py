from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import AuditEvent
from app.schemas import AuditEvent as AuditEventSchema

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("", response_model=List[AuditEventSchema])
@router.get("/", response_model=List[AuditEventSchema], include_in_schema=False)
def list_audit_events(
    event_type: str = None,
    correlation_id: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List audit events."""
    query = db.query(AuditEvent)

    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if correlation_id:
        query = query.filter(AuditEvent.correlation_id == correlation_id)

    events = query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    return events
