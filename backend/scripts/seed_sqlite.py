"""Quick setup for SQLite - no PostgreSQL needed"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import Zone, Agency, Resource
from app.core.database_sqlite import engine, SessionLocal, init_db
from app.core.database import Base
from datetime import datetime

def seed_sqlite():
    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # Create zones (without PostGIS geometry)
    zones_data = [
        {"id": "ZONE_A", "name": "Zone A - Coastal District", "lat": 19.0760, "lon": 72.8777, "pop": 25000, "vuln": 4000},
        {"id": "ZONE_B", "name": "Zone B - Urban Center", "lat": 19.1136, "lon": 72.8697, "pop": 45000, "vuln": 6500},
        {"id": "ZONE_C", "name": "Zone C - Rural Area", "lat": 19.2183, "lon": 72.9781, "pop": 12000, "vuln": 2000},
        {"id": "ZONE_D", "name": "Zone D - Mountain Region", "lat": 19.0330, "lon": 73.0297, "pop": 8000, "vuln": 1500},
        {"id": "ZONE_E", "name": "Zone E - River Basin", "lat": 18.9388, "lon": 72.8354, "pop": 18000, "vuln": 3200}
    ]

    for z in zones_data:
        zone = Zone(
            id=z["id"],
            name=z["name"],
            latitude=z["lat"],
            longitude=z["lon"],
            population=z["pop"],
            vulnerable_population=z["vuln"],
            severity=3.0,
            priority_score=50.0,
            status="active"
        )
        db.add(zone)

    # Create agencies
    agencies_data = [
        {"id": "NDRF", "name": "National Disaster Response Force", "type": "rescue"},
        {"id": "FIRE", "name": "Fire & Rescue Service", "type": "rescue"},
        {"id": "DISTRICT", "name": "District Administration", "type": "government"},
        {"id": "NGO_ALPHA", "name": "NGO Alpha Relief", "type": "ngo"},
        {"id": "MEDICAL", "name": "Medical Corps", "type": "medical"}
    ]

    for a in agencies_data:
        agency = Agency(
            id=a["id"],
            name=a["name"],
            type=a["type"],
            capabilities=[]
        )
        db.add(agency)

    # Create resources
    resources_data = [
        {"id": "R01", "name": "Rescue Team Alpha", "type": "rescue_team", "agency": "NDRF", "lat": 19.0896, "lon": 72.8656, "qty": 1, "unit": "team"},
        {"id": "R02", "name": "Rescue Team Beta", "type": "rescue_team", "agency": "NDRF", "lat": 19.0728, "lon": 72.8826, "qty": 1, "unit": "team"},
        {"id": "R03", "name": "Fire Team Alpha", "type": "rescue_team", "agency": "FIRE", "lat": 19.1197, "lon": 72.8464, "qty": 1, "unit": "team"},
        {"id": "M01", "name": "Medical Kit Stock A", "type": "medical_kit", "agency": "MEDICAL", "lat": 19.0760, "lon": 72.8777, "qty": 200, "unit": "kits"},
        {"id": "W01", "name": "Water Supply Truck 1", "type": "water_liter", "agency": "DISTRICT", "lat": 19.0896, "lon": 72.8656, "qty": 5000, "unit": "liters"},
        {"id": "F01", "name": "Food Distribution Center 1", "type": "food_packet", "agency": "NGO_ALPHA", "lat": 19.0760, "lon": 72.8777, "qty": 8000, "unit": "packets"},
    ]

    for r in resources_data:
        resource = Resource(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            agency_id=r["agency"],
            latitude=r["lat"],
            longitude=r["lon"],
            quantity=r["qty"],
            unit=r["unit"],
            status="available"
        )
        db.add(resource)

    db.commit()
    print("SQLite database seeded successfully")

if __name__ == "__main__":
    seed_sqlite()
