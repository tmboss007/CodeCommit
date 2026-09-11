# NEXUS-R — Agentic Disaster Resource Orchestration Platform

**Problem Statement:** PS20 — Agentic Disaster Relief & Emergency Resource Coordinator  
**Team:** CodeCommit  
**Repository:** https://github.com/tmboss007/CodeCommit

## Overview

NEXUS-R is a closed-loop disaster resource orchestration system that dynamically allocates emergency resources based on real-time situation assessment, priority scoring, and constraint-based optimization.

### Core Capabilities

- Real-time incident reporting and situation analysis
- AI-powered needs assessment and priority scoring
- Duplicate incident detection
- Constraint-based resource optimization (Google OR-Tools)
- Dynamic re-planning when disaster state changes
- Inter-agency coordination with human-in-the-loop approval
- Complete audit trail

## Architecture

```
Field Reports → Situation Agent → Needs Agent → Priority Agent
                                                     ↓
                                        Duplicate Detection Agent
                                                     ↓
                                          Optimization Engine
                                                     ↓
                                          Coordination Agent
                                                     ↓
                                           Human Approval
                                                     ↓
                                        Action & Audit Trail
                                                     ↓
                                         Dynamic Re-planning
```

## Tech Stack

**Frontend:**
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- MapLibre GL JS

**Backend:**
- Python 3.11+
- FastAPI
- PostgreSQL + PostGIS
- Redis
- WebSockets

**Agent Orchestration:**
- LangGraph
- OpenAI API / Anthropic Claude

**Optimization:**
- Google OR-Tools
- NetworkX

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ with PostGIS
- Redis

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Setup database
python -m alembic upgrade head
python scripts/seed_demo_data.py

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with backend URL

# Run dev server
npm run dev
```

### Access

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Demo Scenario

The system simulates a multi-zone disaster response:

1. **Initial State:** 5 zones with varying severity levels
2. **Initial Allocation:** Resources distributed based on priority
3. **Critical Event:** Urgent Zone A escalation injected
4. **Re-planning:** System detects priority shift and reallocates resources
5. **Human Approval:** Operator reviews and approves changes
6. **Execution:** Resources redeployed, audit trail updated

### Demo Controls

- Load Demo Scenario
- Inject Urgent Report
- Block Route
- Disable Resource
- Reset Simulation

## API Overview

```
POST   /api/incidents              Create incident report
GET    /api/incidents              List incidents
GET    /api/zones                  List zones with status
GET    /api/resources              List resources
POST   /api/plans/generate         Generate allocation plan
POST   /api/plans/replan           Trigger re-planning
POST   /api/coordination/tasks/:id/approve
GET    /api/audit                  Audit log
```

See [API.md](./API.md) for full documentation.

## Features

### IMPLEMENTED
- ✅ Incident reporting and ingestion
- ✅ Multi-agent situation analysis pipeline
- ✅ Priority scoring with factor breakdown
- ✅ Constraint-based optimization
- ✅ Resource digital twin
- ✅ Dynamic re-planning on state changes
- ✅ Human-in-the-loop approval workflow
- ✅ Complete audit trail
- ✅ Real-time dashboard with WebSocket updates
- ✅ Interactive map with MapLibre
- ✅ Simulation controls

### SIMULATED (Mock Mode)
- 🔄 IMD weather data (adapter implemented)
- 🔄 GDACS disaster events (adapter implemented)
- 🔄 MOSDAC satellite data (adapter implemented)
- 🔄 Routing/ETA calculation (realistic simulation)

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# End-to-end test
pytest tests/test_e2e_scenario.py
```

## Limitations

This is a hackathon MVP:

- External data sources run in simulation mode
- Routing uses distance-based ETA estimates
- Single-region deployment
- No authentication system
- Simplified resource types
- Demo-scale data only

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [AGENTS.md](./AGENTS.md) - Agent specifications
- [API.md](./API.md) - API reference
- [DEMO.md](./DEMO.md) - Demo walkthrough
- [SETUP.md](./SETUP.md) - Detailed setup guide

## License

MIT

---

🤖 Built for PS20 Hackathon
