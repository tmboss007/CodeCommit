from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas import PlanRequest
from app.services.orchestration import OrchestrationService
from app.models import AppState

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _raise_if_error(result: dict):
    if result.get("error"):
        raise HTTPException(status_code=result.get("status_code") or 400, detail=result)
    return result


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
    orch = OrchestrationService(db)
    card = orch.revise_plan_card()
    state = db.query(AppState).filter(AppState.id == "singleton").first()
    if not state:
        return {"plan_id": None, "delta": None, "revised_plan": None, "plans": []}
    return {
        "plan_id": state.last_plan_id,
        "status": state.last_plan_status,
        "active_plan_id": state.active_plan_id,
        "delta": state.last_delta,
        "unmet_demands": state.last_unmet,
        "explanation": state.last_explanation,
        "blocked_routes": state.blocked_routes,
        "revised_plan": card,
        "plans": orch.list_plans(),
    }


@router.get("")
def list_plans(db: Session = Depends(get_db)):
    orch = OrchestrationService(db)
    return {"active_plan_id": orch._get_state().active_plan_id, "plans": orch.list_plans()}



@router.post("/{plan_id}/approve")
def approve_plan(plan_id: str, db: Session = Depends(get_db)):
    from app.api.ops import snapshot
    result = _raise_if_error(OrchestrationService(db).approve_plan(plan_id))
    result["state"] = snapshot(db)
    return result


@router.post("/{plan_id}/reject")
def reject_plan(plan_id: str, db: Session = Depends(get_db)):
    from app.api.ops import snapshot
    result = _raise_if_error(OrchestrationService(db).reject_plan(plan_id))
    result["state"] = snapshot(db)
    return result
