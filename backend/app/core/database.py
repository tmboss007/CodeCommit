from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def is_sqlite(bind=None) -> bool:
    url = str(bind.url if bind is not None else engine.url)
    return url.startswith("sqlite")


def is_postgres(bind=None) -> bool:
    url = str(bind.url if bind is not None else engine.url)
    return url.startswith("postgresql")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_PG_EXTRAS = [
    "ALTER TABLE zones ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)",
    "ALTER TABLE resources ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)",
    "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)",
    "CREATE INDEX IF NOT EXISTS ix_incidents_zone_id ON incidents (zone_id)",
    "CREATE INDEX IF NOT EXISTS ix_incidents_timestamp ON incidents (timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_incidents_status ON incidents (status)",
    "CREATE INDEX IF NOT EXISTS ix_resources_status ON resources (status)",
    "CREATE INDEX IF NOT EXISTS ix_resources_agency_id ON resources (agency_id)",
    "CREATE INDEX IF NOT EXISTS ix_allocations_plan_id ON allocations (plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_coordination_tasks_plan_id ON coordination_tasks (plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_zones_location ON zones USING GIST (location)",
    "CREATE INDEX IF NOT EXISTS ix_resources_location ON resources USING GIST (location)",
    "CREATE INDEX IF NOT EXISTS ix_incidents_location ON incidents USING GIST (location)",
]


def ensure_schema():
    if is_postgres():
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(bind=engine)
    if is_sqlite():
        statements = [
            "ALTER TABLE app_state ADD COLUMN last_plan_status VARCHAR DEFAULT 'none'",
            "ALTER TABLE app_state ADD COLUMN last_plan_trigger VARCHAR",
            "ALTER TABLE app_state ADD COLUMN active_plan_id VARCHAR",
            "ALTER TABLE coordination_tasks ADD COLUMN plan_id VARCHAR",
        ]
        with engine.begin() as conn:
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
        return
    if is_postgres():
        with engine.begin() as conn:
            for stmt in _PG_EXTRAS:
                conn.execute(text(stmt))
            conn.execute(text(
                "UPDATE zones SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
                "WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL"
            ))
            conn.execute(text(
                "UPDATE resources SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
                "WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL"
            ))
