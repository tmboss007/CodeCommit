from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, Base, ensure_schema, is_sqlite, is_postgres
from app.core.events import event_bus
from app.api import incidents, zones, resources, plans, coordination, audit
from app.api import simulation, ops, events
from app.models import Zone  # noqa: F401 — register models
from app.models import Plan  # noqa: F401


def _boot_schema():
    ensure_schema()
    if not is_sqlite():
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT priority_breakdown FROM zones LIMIT 1"))
            conn.execute(text("SELECT last_plan_status FROM app_state LIMIT 1"))
    except Exception:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _boot_schema()
    yield
    event_bus.close_all()


app = FastAPI(
    title="NEXUS-R API",
    description="Agentic Disaster Resource Orchestration Platform",
    version="1.0.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins + ["http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router)
app.include_router(zones.router)
app.include_router(resources.router)
app.include_router(plans.router)
app.include_router(coordination.router)
app.include_router(audit.router)
app.include_router(simulation.router)
app.include_router(ops.router)
app.include_router(events.router)


@app.get("/")
def root():
    return {"name": "NEXUS-R API", "version": "1.0.0", "status": "operational"}


@app.get("/health")
def health():
    dialect = engine.dialect.name
    postgis = False
    if is_postgres():
        with engine.connect() as conn:
            postgis = bool(conn.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')")
            ).scalar())
    return {"status": "healthy", "database": dialect, "postgis": postgis}
