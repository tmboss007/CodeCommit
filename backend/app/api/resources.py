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
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if payload.status:
        if payload.status == "unavailable":
            return OrchestrationService(db).disable_resource(resource_id)
        resource.status = payload.status
        db.commit()
    return {"id": resource.id, "status": resource.status}
