from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ZoneBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    population: int = 0
    vulnerable_population: int = 0
    severity: float = 0
    priority_score: float = 0
    status: str = "active"

class ZoneCreate(ZoneBase):
    id: str

class Zone(ZoneBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class IncidentBase(BaseModel):
    source: str
    report_text: str
    source_reference: Optional[str] = None

class IncidentCreate(IncidentBase):
    pass

class Incident(IncidentBase):
    id: str
    zone_id: str
    incident_type: Optional[str]
    timestamp: datetime
    affected_population: Optional[int]
    vulnerable_population: Optional[int]
    confidence: Optional[float]
    status: str
    duplicate_group_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class NeedBase(BaseModel):
    resource_type: str
    quantity_required: float
    urgency: float = 0.5
    unit: Optional[str] = None

class Need(NeedBase):
    id: str
    incident_id: Optional[str]
    zone_id: Optional[str]
    quantity_fulfilled: float
    quantity_remaining: Optional[float]

    class Config:
        from_attributes = True

class ResourceBase(BaseModel):
    name: str
    type: str
    agency_id: str
    latitude: Optional[float]
    longitude: Optional[float]
    quantity: Optional[float]
    unit: Optional[str]
    capacity: Optional[float]
    capabilities: Optional[List[str]]
    status: str = "available"

class ResourceCreate(ResourceBase):
    id: str

class Resource(ResourceBase):
    id: str
    current_zone_id: Optional[str]
    available_at: Optional[datetime]
    eta_minutes: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class AllocationBase(BaseModel):
    resource_id: str
    zone_id: str
    quantity: Optional[float]
    priority: Optional[float]
    eta_minutes: Optional[int]
    reason: Optional[str]

class Allocation(AllocationBase):
    id: str
    status: str
    plan_id: Optional[str]
    created_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True

class CoordinationTaskBase(BaseModel):
    agency_id: str
    action: str

class CoordinationTask(CoordinationTaskBase):
    id: str
    allocation_id: Optional[str]
    status: str
    assigned_at: datetime
    approved_at: Optional[datetime]

    class Config:
        from_attributes = True

class AuditEventCreate(BaseModel):
    actor: Optional[str]
    agent: Optional[str]
    event_type: str
    description: str
    input_reference: Optional[str]
    previous_state: Optional[dict]
    new_state: Optional[dict]
    reason: Optional[str]
    correlation_id: Optional[str]

class AuditEvent(AuditEventCreate):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True

class PlanRequest(BaseModel):
    trigger: str = "manual"
    correlation_id: Optional[str] = None

class PlanResponse(BaseModel):
    plan_id: str
    allocations: List[Allocation]
    unmet_demands: List[dict]
    coordination_tasks: List[CoordinationTask]
    reason: str
    timestamp: datetime
