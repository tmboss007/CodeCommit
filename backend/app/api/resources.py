from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models import Resource
from app.schemas import Resource as ResourceSchema
from app.services.orchestration import OrchestrationService

router = APIRouter(prefix="/api/resources", tags=["resources"])


class ResourcePatch(BaseModel):
    status: Optional[str] = None
    current_zone_id: Optional[str] = None
    eta_minutes: Optional[int] = None
    reason: Optional[str] = None


@router.get("", response_model=List[ResourceSchema])
@router.get("/", response_model=List[ResourceSchema], include_in_schema=False)
def list_resources(status: str = None, type: str = None, agency_id: str = None, db: Session = Depends(get_db)):
    query = db.query(Resource)
    if status:
        query = query.filter(Resource.status == status)
    if type:
        query = query.filter(Resource.type == type)
    if agency_id:
        query = query.filter(Resource.agency_id == agency_id)
    return query.all()


@router.patch("/{resource_id}")
def patch_resource(resource_id: str, payload: ResourcePatch, db: Session = Depends(get_db)):
    data = payload.dict(exclude_unset=True)
    reason = data.pop("reason", None)
    if not data:
        raise HTTPException(status_code=400, detail={"error": "empty_patch", "details": ["No resource fields to update"]})
    result = OrchestrationService(db).update_resource(resource_id, data, actor="operator", reason=reason)
    if result.get("error"):
        raise HTTPException(status_code=result.get("status_code") or 400, detail=result)
    return result
