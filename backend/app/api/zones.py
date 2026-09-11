from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models import Zone
from app.schemas import Zone as ZoneSchema

router = APIRouter(prefix="/api/zones", tags=["zones"])

@router.get("", response_model=List[ZoneSchema])
@router.get("/", response_model=List[ZoneSchema], include_in_schema=False)
def list_zones(db: Session = Depends(get_db)):
    """List all zones with current status."""
    zones = db.query(Zone).all()
    return zones

@router.get("/{zone_id}", response_model=ZoneSchema)
def get_zone(zone_id: str, db: Session = Depends(get_db)):
    """Get zone details."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone
