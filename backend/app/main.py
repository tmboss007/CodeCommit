from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import incidents, zones, resources, plans, coordination, audit

app = FastAPI(
    title="NEXUS-R API",
    description="Agentic Disaster Resource Orchestration Platform",
    version="1.0.0"
)

# CORS
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(incidents.router)
app.include_router(zones.router)
app.include_router(resources.router)
app.include_router(plans.router)
app.include_router(coordination.router)
app.include_router(audit.router)

@app.get("/")
def root():
    return {
        "name": "NEXUS-R API",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
