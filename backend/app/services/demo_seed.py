from datetime import datetime
from app.models import Zone, Agency, Resource

ZONES = [
    {"id": "ZONE_A", "name": "Zone A — Coastal District", "lat": 19.0760, "lon": 72.8777, "pop": 25000, "vuln": 4000, "severity": 6.0},
    {"id": "ZONE_B", "name": "Zone B — Urban Center", "lat": 19.1136, "lon": 72.8697, "pop": 45000, "vuln": 6500, "severity": 5.0},
    {"id": "ZONE_C", "name": "Zone C — Rural Area", "lat": 19.2183, "lon": 72.9781, "pop": 12000, "vuln": 2000, "severity": 4.0},
    {"id": "ZONE_D", "name": "Zone D — Mountain Region", "lat": 19.0330, "lon": 73.0297, "pop": 8000, "vuln": 1500, "severity": 7.5},
    {"id": "ZONE_E", "name": "Zone E — River Basin", "lat": 18.9388, "lon": 72.8354, "pop": 18000, "vuln": 3200, "severity": 6.5},
]

AGENCIES = [
    {"id": "NDRF", "name": "National Disaster Response Force", "type": "rescue"},
    {"id": "FIRE", "name": "Fire & Rescue Service", "type": "rescue"},
    {"id": "DISTRICT", "name": "District Administration", "type": "government"},
    {"id": "NGO_ALPHA", "name": "NGO Alpha Relief", "type": "ngo"},
    {"id": "MEDICAL", "name": "Medical Corps", "type": "medical"},
]

RESOURCES = [
    {"id": "R01", "name": "Rescue Team Alpha", "type": "rescue_team", "agency": "NDRF", "lat": 19.0896, "lon": 72.8656, "qty": 1, "unit": "team", "caps": ["flood_rescue"]},
    {"id": "R02", "name": "Rescue Team Beta", "type": "rescue_team", "agency": "NDRF", "lat": 19.0728, "lon": 72.8826, "qty": 1, "unit": "team", "caps": ["flood_rescue"]},
    {"id": "R03", "name": "Rescue Team Gamma", "type": "rescue_team", "agency": "NDRF", "lat": 19.0330, "lon": 73.0297, "qty": 1, "unit": "team", "caps": ["mountain_rescue"]},
    {"id": "R04", "name": "Fire Team Alpha", "type": "rescue_team", "agency": "FIRE", "lat": 19.1197, "lon": 72.8464, "qty": 1, "unit": "team", "caps": ["urban_rescue"]},
    {"id": "R05", "name": "Fire Team Beta", "type": "rescue_team", "agency": "FIRE", "lat": 19.0171, "lon": 72.8560, "qty": 1, "unit": "team", "caps": ["urban_rescue"]},
    {"id": "M01", "name": "Medical Kit Stock A", "type": "medical_kit", "agency": "MEDICAL", "lat": 19.0760, "lon": 72.8777, "qty": 200, "unit": "kits", "caps": ["trauma"]},
    {"id": "M02", "name": "Medical Kit Stock B", "type": "medical_kit", "agency": "DISTRICT", "lat": 19.1136, "lon": 72.8697, "qty": 150, "unit": "kits", "caps": ["first_aid"]},
    {"id": "M03", "name": "Field Hospital Unit", "type": "medical_kit", "agency": "MEDICAL", "lat": 19.0896, "lon": 72.8656, "qty": 80, "unit": "kits", "caps": ["emergency_beds"]},
    {"id": "W01", "name": "Water Supply Truck 1", "type": "water_liter", "agency": "DISTRICT", "lat": 19.0896, "lon": 72.8656, "qty": 5000, "unit": "liters", "caps": ["potable"]},
    {"id": "W02", "name": "Water Supply Truck 2", "type": "water_liter", "agency": "NGO_ALPHA", "lat": 19.0330, "lon": 73.0297, "qty": 3500, "unit": "liters", "caps": ["potable"]},
    {"id": "W03", "name": "Water Bladder Cache", "type": "water_liter", "agency": "DISTRICT", "lat": 18.9388, "lon": 72.8354, "qty": 4000, "unit": "liters", "caps": ["bulk"]},
    {"id": "F01", "name": "Food Distribution Center 1", "type": "food_packet", "agency": "NGO_ALPHA", "lat": 19.0760, "lon": 72.8777, "qty": 8000, "unit": "packets", "caps": ["ready_to_eat"]},
    {"id": "F02", "name": "Food Distribution Center 2", "type": "food_packet", "agency": "DISTRICT", "lat": 19.2183, "lon": 72.9781, "qty": 5000, "unit": "packets", "caps": ["ready_to_eat"]},
    {"id": "S01", "name": "Emergency Shelter Camp A", "type": "shelter_capacity", "agency": "DISTRICT", "lat": 19.1136, "lon": 72.8697, "qty": 1000, "unit": "persons", "caps": ["family"]},
    {"id": "S02", "name": "Emergency Shelter Camp B", "type": "shelter_capacity", "agency": "NGO_ALPHA", "lat": 19.0330, "lon": 73.0297, "qty": 800, "unit": "persons", "caps": ["family"]},
]

INITIAL_REPORTS = [
    {
        "zone_id": "ZONE_A",
        "source": "field_officer",
        "text": "Zone A coastal flooding. Approximately 800 people affected in low-lying wards. Water supply disrupted.",
    },
    {
        "zone_id": "ZONE_B",
        "source": "district_control",
        "text": "Zone B urban center reporting moderate flooding and crowding. About 1200 people displaced from informal settlements.",
    },
    {
        "zone_id": "ZONE_C",
        "source": "local_admin",
        "text": "Zone C rural area has limited road access and 200 people affected by moderate waterlogging.",
    },
    {
        "zone_id": "ZONE_D",
        "source": "ndrf_spotter",
        "text": "Zone D mountain landslide. Critical rescue required. Approximately 400 people isolated on the slope. Immediate rescue teams needed.",
    },
    {
        "zone_id": "ZONE_E",
        "source": "ngo_alpha",
        "text": "Zone E river basin. High shelter and water demand. About 900 people need drinking water and temporary shelter.",
    },
]

URGENT_ZONE_A_REPORT = (
    "Zone A water level has risen rapidly. Approximately 2,000 additional people affected. "
    "Two rescue routes are becoming inaccessible. Immediate evacuation support required."
)


def seed_base_entities(db):
    for z in ZONES:
        db.add(Zone(
            id=z["id"],
            name=z["name"],
            latitude=z["lat"],
            longitude=z["lon"],
            population=z["pop"],
            vulnerable_population=z["vuln"],
            severity=z["severity"],
            priority_score=50.0,
            status="active",
        ))
    for a in AGENCIES:
        db.add(Agency(id=a["id"], name=a["name"], type=a["type"], capabilities=[]))
    for r in RESOURCES:
        db.add(Resource(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            agency_id=r["agency"],
            latitude=r["lat"],
            longitude=r["lon"],
            quantity=r["qty"],
            unit=r["unit"],
            capabilities=r["caps"],
            status="available",
        ))
    db.commit()
