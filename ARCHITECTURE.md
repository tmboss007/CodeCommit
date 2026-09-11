# CodeCommit System Architecture

## Overview

CodeCommit is a closed-loop emergency resource orchestration platform. It combines structured incident interpretation with deterministic scoring, needs calculation, and OR-Tools allocation.

Internal codebase name remains NEXUS-R in some modules.

## Core Principle

Static allocation is insufficient. When incident state changes, the system reassesses priority, detects conflicts, re-optimizes, and requests human approval.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL DATA SOURCES                    │
│  IMD Weather  │  GDACS Events  │  MOSDAC Satellite  │  Field│
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                      │
│  Report Validation  │  Normalization  │  Deduplication      │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATION                     │
│                                                               │
│  ┌─────────────────┐      ┌────────────────┐               │
│  │ Situation Agent │ ───▶ │  Needs Agent   │               │
│  └─────────────────┘      └────────┬───────┘               │
│         │                           │                        │
│         ▼                           ▼                        │
│  ┌─────────────────┐      ┌────────────────┐               │
│  │ Duplicate Agent │      │ Priority Agent │               │
│  └─────────────────┘      └────────┬───────┘               │
│                                     │                        │
└─────────────────────────────────────┼────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  OPERATIONAL STATE DATABASE                  │
│  Zones  │  Incidents  │  Needs  │  Resources  │  Agencies  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                     OPTIMIZATION ENGINE                      │
│                                                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Google OR-Tools Constraint Solver                  │    │
│  │  • Maximize priority-weighted coverage              │    │
│  │  • Minimize response time                           │    │
│  │  • Respect resource capacity constraints            │    │
│  │  • Match resource capabilities to needs             │    │
│  └────────────────────────────────────────────────────┘    │
│                                                               │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                   COORDINATION LAYER                         │
│                                                               │
│  ┌─────────────────┐      ┌────────────────────────────┐   │
│  │ Coordination    │ ───▶ │  Human Approval Workflow   │   │
│  │ Agent           │      └────────────────────────────┘   │
│  └─────────────────┘                                         │
│         │                                                     │
└─────────┼─────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    ACTION & DISPATCH                         │
│  Update Resource State  │  Send Agency Tasks  │  Notify     │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                   AUDIT & EVENT LOG                          │
│  Complete traceability with correlation IDs                  │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼ (Feedback Loop)
┌─────────────────────────────────────────────────────────────┐
│                   RE-PLANNING AGENT                          │
│  • Monitors state changes                                    │
│  • Detects material changes (priority, severity, resources)  │
│  • Triggers re-optimization when thresholds exceeded         │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Ingestion Layer

**Purpose**: Normalize diverse data sources into unified format

**Components**:
- Field report API endpoints
- External data adapters (IMD, GDACS, MOSDAC)
- Validation and sanitization
- Timestamp normalization

**Implementation**: FastAPI routes with adapter pattern

### 2. Agent Orchestration

**Purpose**: Extract insights and make recommendations

#### Situation Agent
- **Input**: Raw incident report text
- **Output**: Structured incident data (type, location, affected population, severity)
- **Technology**: LLM with structured output (GPT-4/Claude)
- **Key Decision**: What kind of disaster? How severe?

#### Needs Assessment Agent
- **Input**: Incident details (population, type, severity)
- **Output**: Required resources with quantities
- **Technology**: Rule-based calculator with LLM enhancement
- **Key Decision**: What resources are needed and how much?

#### Priority Agent
- **Input**: Incident severity, population, vulnerability, resource deficit
- **Output**: Priority score (0-100) with factor breakdown
- **Technology**: Configurable weighted scoring model
- **Key Decision**: Which zones need help most urgently?

#### Duplicate Detection Agent
- **Input**: New report + existing incidents
- **Output**: Similarity score and duplicate flag
- **Technology**: LLM semantic comparison + geospatial proximity
- **Key Decision**: Is this a new incident or duplicate report?

### 3. Operational State Database

**Technology**: PostgreSQL + PostGIS

**Key Tables**:
- `zones`: Geographic regions with current state
- `incidents`: Reported events
- `needs`: Required resources per zone/incident
- `resources`: Available assets (teams, supplies)
- `allocations`: Resource-to-zone assignments
- `audit_events`: Complete action history

**Geospatial Features**:
- Point geometries for zones and resources
- Distance calculations for routing
- Spatial indexes for performance

### 4. Optimization Engine

**Technology**: Google OR-Tools (SCIP solver)

**Objective Function**:
```
Maximize: Σ (priority_i × distance_penalty_ij × need_match_ij × allocation_ij)
```

**Constraints**:
- Each resource ≤ total capacity
- Each zone need ≥ 0 (cannot over-satisfy)
- Resource-zone compatibility
- Resource availability status

**Output**:
- Allocation plan
- Unmet demands
- Objective value
- Constraint violations (if any)

**Fallback**: Greedy algorithm if solver unavailable

### 5. Coordination Layer

**Purpose**: Translate allocations into actionable tasks

**Coordination Agent**:
- Maps allocations to agency tasks
- Formats human-readable actions
- Detects conflicts (double-booking, incompatible capabilities)

**Human-in-the-Loop**:
- High-impact decisions require approval
- Operator can approve/modify/reject
- Approval status tracked in database

### 6. Re-planning Agent

**Purpose**: Detect when system state requires re-optimization

**Triggers**:
- Priority change > 15 points
- Severity change > 2 levels
- Population increase > 30%
- Resource unavailable
- Critical deficit > 40%

**Process**:
1. Compare old state vs new state
2. Evaluate trigger thresholds
3. If triggered: re-run optimization
4. Compute allocation delta
5. Generate revised coordination tasks
6. Request human approval

**Key Innovation**: System adapts automatically to changing conditions

### 7. Audit System

**Purpose**: Complete traceability and accountability

**Features**:
- Every state change logged
- Correlation IDs trace related events
- Agent reasoning captured
- Before/after state snapshots
- Human actor attribution

## Technology Stack

### Backend
- **Framework**: FastAPI (async, high performance)
- **Database**: PostgreSQL 14+ with PostGIS
- **Cache**: Redis (session state, real-time updates)
- **Optimization**: Google OR-Tools
- **Agents**: LangGraph + OpenAI/Anthropic
- **Geospatial**: GeoPy, Shapely

### Frontend
- **Framework**: Next.js 14 (React 18)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Maps**: MapLibre GL JS
- **State**: SWR for data fetching

### Infrastructure
- **Deployment**: Docker containers (not included in MVP)
- **API**: REST + WebSockets for real-time updates
- **Monitoring**: Structured logging with correlation IDs

## Data Flow: Incident to Allocation

1. **Report received** → API endpoint
2. **Situation Agent** → Extracts structured data
3. **Save to DB** → Incident + Needs records
4. **Priority Agent** → Updates zone priority score
5. **Duplicate Agent** → Checks for overlaps
6. **Re-planning Agent** → Evaluates if triggers met
7. If triggered:
   - **Optimization Engine** → Computes new allocation
   - **Coordination Agent** → Generates tasks
   - **Human Approval** → Operator reviews
   - **Action** → Update resource states
   - **Audit** → Log complete workflow

## Scalability Considerations

**Current (MVP)**:
- Single-region
- Synchronous agent execution
- In-memory optimization

**Production Path**:
- Multi-region with geographic partitioning
- Async agent orchestration (Celery/RQ)
- Distributed optimization for large resource sets
- Read replicas for dashboard queries
- Message queue for real-time updates
- Caching layer for frequently accessed data

## Security

**Current**: Development mode, no auth

**Production Requirements**:
- Role-based access control (RBAC)
- API key authentication for external systems
- Audit log immutability
- Encrypted secrets storage
- HTTPS only
- Rate limiting

## External Integration Strategy

**Adapter Pattern**:
```
WeatherProvider (interface)
  ├─ IMDWeatherProvider (live)
  └─ MockWeatherProvider (simulation)
```

**Benefits**:
- Swap implementations without code changes
- Test without live API dependencies
- Graceful degradation if external service fails

**Mock Mode**: Demo runs fully offline with realistic sample data
