from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Zone(Base):
    __tablename__ = "zones"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    population = Column(Integer, default=0)
    vulnerable_population = Column(Integer, default=0)
    severity = Column(Float, default=0)
    priority_score = Column(Float, default=0)
    priority_breakdown = Column(JSON)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incidents = relationship("Incident", back_populates="zone")
    needs = relationship("Need", back_populates="zone")
    allocations = relationship("Allocation", back_populates="zone")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True)
    zone_id = Column(String, ForeignKey("zones.id"), nullable=False)
    source = Column(String, nullable=False)
    source_reference = Column(String)
    report_text = Column(Text, nullable=False)
    incident_type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    affected_population = Column(Integer)
    vulnerable_population = Column(Integer)
    confidence = Column(Float)
    status = Column(String, default="active")
    duplicate_group_id = Column(String)
    duplicate_status = Column(String, default="NEW")
    analysis_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    zone = relationship("Zone", back_populates="incidents")
    needs = relationship("Need", back_populates="incident")

class Need(Base):
    __tablename__ = "needs"

    id = Column(String, primary_key=True)
    incident_id = Column(String, ForeignKey("incidents.id"))
    zone_id = Column(String, ForeignKey("zones.id"))
    resource_type = Column(String, nullable=False)
    quantity_required = Column(Float, nullable=False)
    quantity_fulfilled = Column(Float, default=0)
    quantity_remaining = Column(Float)
    urgency = Column(Float, default=0.5)
    unit = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incident = relationship("Incident", back_populates="needs")
    zone = relationship("Zone", back_populates="needs")

class Agency(Base):
    __tablename__ = "agencies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)
    contact = Column(String)
    capabilities = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    resources = relationship("Resource", back_populates="agency")
    tasks = relationship("CoordinationTask", back_populates="agency")

class Resource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    agency_id = Column(String, ForeignKey("agencies.id"), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    quantity = Column(Float)
    unit = Column(String)
    capacity = Column(Float)
    capabilities = Column(JSON)
    status = Column(String, default="available")
    current_zone_id = Column(String, ForeignKey("zones.id"))
    available_at = Column(DateTime)
    eta_minutes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agency = relationship("Agency", back_populates="resources")
    allocations = relationship("Allocation", back_populates="resource")

class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(String, primary_key=True)
    resource_id = Column(String, ForeignKey("resources.id"), nullable=False)
    zone_id = Column(String, ForeignKey("zones.id"), nullable=False)
    quantity = Column(Float)
    priority = Column(Float)
    eta_minutes = Column(Integer)
    reason = Column(Text)
    status = Column(String, default="pending")
    plan_id = Column(String)
    from_zone_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    approved_by = Column(String)

    resource = relationship("Resource", back_populates="allocations")
    zone = relationship("Zone", back_populates="allocations")
    tasks = relationship("CoordinationTask", back_populates="allocation")

class CoordinationTask(Base):
    __tablename__ = "coordination_tasks"

    id = Column(String, primary_key=True)
    agency_id = Column(String, ForeignKey("agencies.id"), nullable=False)
    allocation_id = Column(String, ForeignKey("allocations.id"))
    action = Column(Text, nullable=False)
    status = Column(String, default="pending")
    assigned_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)

    agency = relationship("Agency", back_populates="tasks")
    allocation = relationship("Allocation", back_populates="tasks")

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String)
    agent = Column(String)
    event_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    input_reference = Column(String)
    previous_state = Column(JSON)
    new_state = Column(JSON)
    reason = Column(Text)
    correlation_id = Column(String, index=True)

class ReplanningEvent(Base):
    __tablename__ = "replanning_events"

    id = Column(String, primary_key=True)
    trigger = Column(String, nullable=False)
    old_plan_id = Column(String)
    new_plan_id = Column(String)
    changed_zones = Column(JSON)
    changed_resources = Column(JSON)
    delta = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    correlation_id = Column(String)


class AppState(Base):
    __tablename__ = "app_state"

    id = Column(String, primary_key=True, default="singleton")
    last_plan_id = Column(String)
    last_snapshot = Column(JSON)
    last_delta = Column(JSON)
    last_unmet = Column(JSON)
    last_explanation = Column(Text)
    blocked_routes = Column(JSON)
    data_mode = Column(String, default="SIMULATION")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
