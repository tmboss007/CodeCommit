from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, Base, ensure_schema
from app.api import incidents, zones, resources, plans, coordination, audit
from app.api import simulation, ops
from app.models import Zone  # noqa: F401 — register models
from app.models import Plan  # noqa: F401

app = FastAPI(
    title="NEXUS-R API",
    description="Agentic Disaster Resource Orchestration Platform",
    version="1.0.0",
    redirect_slashes=False,
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


@app.on_event("startup")
def startup():
    ensure_schema()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT priority_breakdown FROM zones LIMIT 1"))
            conn.execute(text("SELECT last_plan_status FROM app_state LIMIT 1"))
    except Exception:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"name": "NEXUS-R API", "version": "1.0.0", "status": "operational"}


@app.get("/health")
def health():
    return {"status": "healthy"}
