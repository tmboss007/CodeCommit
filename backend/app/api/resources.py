from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import Resource
from app.schemas import Resource as ResourceSchema

router = APIRouter(prefix="/api/resources", tags=["resources"])

@router.get("/", response_model=List[ResourceSchema])
def list_resources(
    status: str = None,
    type: str = None,
    db: Session = Depends(get_db)
):
    """List resources with filters."""
    query = db.query(Resource)

    if status:
        query = query.filter(Resource.status == status)
    if type:
        query = query.filter(Resource.type == type)

    resources = query.all()
    return resources
