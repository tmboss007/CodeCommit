from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db, engine, SessionLocal, Base
from app.models import CoordinationTask, Allocation, Resource, AuditEvent
from app.schemas import CoordinationTask as TaskSchema
from app.services.orchestration import OrchestrationService
import uuid

router = APIRouter(prefix="/api/coordination", tags=["coordination"])

@router.get("/tasks", response_model=list[TaskSchema])
def list_tasks(status: str = None, agency_id: str = None, db: Session = Depends(get_db)):
    query = db.query(CoordinationTask)
    if status:
        query = query.filter(CoordinationTask.status == status)
    if agency_id:
        query = query.filter(CoordinationTask.agency_id == agency_id)
    return query.order_by(CoordinationTask.assigned_at.desc()).all()


@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: str, db: Session = Depends(get_db)):
    orch = OrchestrationService(db)
    result = orch.approve_task(task_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.post("/tasks/{task_id}/reject")
def reject_task(task_id: str, db: Session = Depends(get_db)):
    orch = OrchestrationService(db)
    result = orch.reject_task(task_id)
    if result.get("error"):
        raise HTTPException(status_code=404, detail="Task not found")
    return result
