from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import PlanRequest
from app.services.orchestration import OrchestrationService
from app.models import AppState

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("/generate")
def generate_plan(request: PlanRequest, db: Session = Depends(get_db)):
    orchestrator = OrchestrationService(db)
    return orchestrator.generate_allocation_plan(request.correlation_id, trigger=request.trigger)


@router.post("/replan")
def trigger_replan(request: PlanRequest, db: Session = Depends(get_db)):
    orchestrator = OrchestrationService(db)
    return orchestrator.generate_allocation_plan(request.correlation_id, trigger=request.trigger or "replan")


@router.get("/latest")
def latest_plan(db: Session = Depends(get_db)):
    state = db.query(AppState).filter(AppState.id == "singleton").first()
    if not state:
        return {"plan_id": None, "delta": None}
    return {
        "plan_id": state.last_plan_id,
        "delta": state.last_delta,
        "unmet_demands": state.last_unmet,
        "explanation": state.last_explanation,
        "blocked_routes": state.blocked_routes,
    }
