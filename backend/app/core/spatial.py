from sqlalchemy import text
from app.core.database import is_postgres
from app.models import Zone
from app.services.priority import calculate_distance_km


def sync_point_locations(db) -> None:
    """Backfill PostGIS points from lat/lon. No-op on SQLite."""
    bind = db.get_bind()
    if not is_postgres(bind):
        return
    db.execute(text(
        "UPDATE zones SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    ))
    db.execute(text(
        "UPDATE resources SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
    ))
    db.execute(text(
        "UPDATE incidents i SET location = z.location FROM zones z "
        "WHERE i.zone_id = z.id AND z.location IS NOT NULL"
    ))
    db.commit()


def nearest_zone_id(db, lat, lon) -> str:
    if lat is None or lon is None:
        return "ZONE_A"
    bind = db.get_bind()
    if is_postgres(bind):
        row = db.execute(
            text(
                "SELECT id FROM zones WHERE location IS NOT NULL "
                "ORDER BY location <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) LIMIT 1"
            ),
            {"lon": float(lon), "lat": float(lat)},
        ).first()
        if row:
            return row[0]
    zones = db.query(Zone).all()
    if not zones:
        return "ZONE_A"
    best = min(
        zones,
        key=lambda z: calculate_distance_km(float(lat), float(lon), z.latitude, z.longitude),
    )
    return best.id


def distance_meters_postgis(db, lon1, lat1, lon2, lat2) -> float:
    """ST_DistanceSphere between two WGS84 points. Postgres only."""
    return float(db.execute(
        text(
            "SELECT ST_DistanceSphere("
            "ST_SetSRID(ST_MakePoint(:lon1, :lat1), 4326), "
            "ST_SetSRID(ST_MakePoint(:lon2, :lat2), 4326))"
        ),
        {"lon1": lon1, "lat1": lat1, "lon2": lon2, "lat2": lat2},
    ).scalar())
