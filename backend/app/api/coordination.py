from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.models import CoordinationTask, Allocation
from app.schemas import CoordinationTask as TaskSchema

router = APIRouter(prefix="/api/coordination", tags=["coordination"])

@router.get("/tasks", response_model=List[TaskSchema])
def list_tasks(
    status: str = None,
    agency_id: str = None,
    db: Session = Depends(get_db)
):
    """List coordination tasks."""
    query = db.query(CoordinationTask)

    if status:
        query = query.filter(CoordinationTask.status == status)
    if agency_id:
        query = query.filter(CoordinationTask.agency_id == agency_id)

    tasks = query.order_by(CoordinationTask.assigned_at.desc()).all()
    return tasks

@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: str, db: Session = Depends(get_db)):
    """Approve coordination task."""
    task = db.query(CoordinationTask).filter(CoordinationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "approved"
    task.approved_at = datetime.utcnow()

    # Update allocation status
    if task.allocation_id:
        allocation = db.query(Allocation).filter(Allocation.id == task.allocation_id).first()
        if allocation:
            allocation.status = "approved"
            allocation.approved_at = datetime.utcnow()

    db.commit()

    return {"status": "approved", "task_id": task_id}

@router.post("/tasks/{task_id}/reject")
def reject_task(task_id: str, db: Session = Depends(get_db)):
    """Reject coordination task."""
    task = db.query(CoordinationTask).filter(CoordinationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "rejected"

    if task.allocation_id:
        allocation = db.query(Allocation).filter(Allocation.id == task.allocation_id).first()
        if allocation:
            allocation.status = "rejected"

    db.commit()

    return {"status": "rejected", "task_id": task_id}
