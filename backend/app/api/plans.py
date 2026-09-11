from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import PlanRequest, PlanResponse
from app.services.orchestration import OrchestrationService

router = APIRouter(prefix="/api/plans", tags=["plans"])

@router.post("/generate", response_model=dict)
def generate_plan(request: PlanRequest, db: Session = Depends(get_db)):
    """Generate new allocation plan."""
    orchestrator = OrchestrationService(db)
    plan = orchestrator.generate_allocation_plan(request.correlation_id)
    return plan

@router.post("/replan", response_model=dict)
def trigger_replan(request: PlanRequest, db: Session = Depends(get_db)):
    """Trigger re-planning based on state changes."""
    orchestrator = OrchestrationService(db)
    plan = orchestrator.generate_allocation_plan(request.correlation_id)
    return plan
