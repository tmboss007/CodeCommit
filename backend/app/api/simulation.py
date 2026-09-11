from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, engine, SessionLocal, Base
from app.services.orchestration import OrchestrationService
from app.models import Resource, AppState

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def _fresh_service():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    return db, OrchestrationService(db)


@router.post("/reset")
def reset():
    db = None
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        return OrchestrationService(db).reset_world()
    finally:
        if db:
            db.close()


@router.post("/load-demo")
def load_demo():
    db = None
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        return OrchestrationService(db).load_demo()
    finally:
        if db:
            db.close()


@router.post("/inject-event")
def inject_event(db: Session = Depends(get_db)):
    return OrchestrationService(db).inject_urgent_zone_a()


@router.post("/inject-urgent-report")
def inject_urgent(db: Session = Depends(get_db)):
    return OrchestrationService(db).inject_urgent_zone_a()


@router.post("/block-route")
def block_route(zone_id: str = "ZONE_A", db: Session = Depends(get_db)):
    return OrchestrationService(db).block_route(zone_id)


@router.post("/disable-resource")
def disable_resource(resource_id: str = None, db: Session = Depends(get_db)):
    orch = OrchestrationService(db)
    if not resource_id:
        resource = db.query(Resource).filter(Resource.status == "available").first()
        if not resource:
            raise HTTPException(status_code=400, detail="No available resource")
        resource_id = resource.id
    return orch.disable_resource(resource_id)


@router.post("/increase-demand")
def increase_demand(zone_id: str = "ZONE_A", db: Session = Depends(get_db)):
    return OrchestrationService(db).increase_demand(zone_id)


@router.post("/run-replan")
def run_replan(db: Session = Depends(get_db)):
    return OrchestrationService(db).generate_allocation_plan(trigger="manual_replan")
