# NEXUS-R Demo Script

## Pre-Demo Setup (5 minutes before)

1. **Backend running**: `uvicorn app.main:app --reload` at http://localhost:8000
2. **Frontend running**: `npm run dev` at http://localhost:3000
3. **Database seeded** with 5 zones and resources
4. **Browser tabs open**:
   - Tab 1: Command Center (/)
   - Tab 2: Incidents (/incidents)
   - Tab 3: Coordination (/coordination)
   - Tab 4: Audit Log (/audit)

## Demo Flow (8-10 minutes)

### PART 1: Initial State (1 min)

**Show Command Center Dashboard**

"This is NEXUS-R, our agentic disaster resource orchestration platform. We're monitoring 5 zones across the region."

**Point out key elements:**
- Zone priority scores (sorted by urgency)
- Real-time resource availability
- Activity stream showing agent actions

### PART 2: Incident Reporting (2 min)

**Navigate to Incidents page**

"Let me demonstrate how the system handles a new disaster report."

**Submit incident:**
```
Severe flooding reported in Zone A coastal area. Water level rising rapidly due to dam overflow. Approximately 1,800 people affected, including 250 elderly residents in care facilities. Two main evacuation routes are now blocked. Emergency rescue and medical support urgently required.
```

**Watch agent pipeline execute:**

1. ✅ **Situation Agent** - "Extracts structured information: flood type, 1,800 affected, 250 vulnerable"
2. ✅ **Needs Assessment Agent** - "Calculates requirements: rescue teams, medical kits, water, food"
3. ✅ **Priority Agent** - "Updates Zone A priority score based on severity and vulnerability"
4. ✅ **Duplicate Detection Agent** - "Checks if this overlaps with existing reports"

**Show incident details:**
- Confidence score
- Extracted incident type
- Calculated needs
- Updated zone priority

### PART 3: Resource Allocation (2 min)

**Navigate to Plans page or trigger via API**

"Now the optimization engine allocates resources based on priority and constraints."

**Show allocation plan:**
- Resources assigned to Zone A
- ETA calculations
- Allocation reasoning (priority-based, distance-weighted)
- Unmet demands (if any)

**Point out:**
- "This uses Google OR-Tools for constraint-based optimization"
- "Not random or hardcoded - actual optimization algorithm"
- "Considers: priority, distance, resource type matching, capacity"

### PART 4: Coordination Tasks (1 min)

**Navigate to Coordination page**

"The system generates actionable tasks for each agency."

**Show task list:**
- NDRF: Deploy Rescue Team Alpha to Zone A
- Medical Corps: Deliver 60 medical kits
- District Admin: Water supply truck deployment

**Demonstrate human-in-the-loop:**
- Click "Approve" on a task
- Show status change
- Emphasize: "High-impact decisions require human approval"

### PART 5: Dynamic Re-planning (3 min)

**THIS IS THE KEY DIFFERENTIATOR**

"Now here's what makes this system truly agentic - watch what happens when conditions change."

**Submit urgent escalation:**
```
URGENT UPDATE - Zone A: Situation deteriorating. Dam breach imminent. Water rising 2 feet per hour. Additional 2,000 people now at risk. Hospital access road flooded. Critical evacuation needed within next 2 hours.
```

**Watch the system respond:**

1. ✅ **Situation Agent** processes update
2. ✅ **Zone A priority** jumps from 72 → 96
3. ✅ **Re-planning Agent** detects critical state change
4. ✅ **Optimization** recalculates allocation
5. ✅ **Shows allocation DELTA**:
   - BEFORE: 2 rescue teams in Zone A, 3 in Zone D
   - AFTER: 4 rescue teams in Zone A, 1 in Zone D
   - Reason: Priority increase, critical rescue deficit

**Show audit trail:**
- Every decision logged
- Correlation IDs trace workflow
- Complete transparency

### PART 6: Audit & Observability (1 min)

**Navigate to Audit Log**

"Everything is traceable:"
- Incident received
- Agent analysis
- Priority recalculation
- Resource reallocation
- Human approvals
- System reasoning

**Emphasize:**
- "No black box - every decision explained"
- "Full accountability for disaster response"

## Key Points to Emphasize

1. **Multi-agent orchestration**: 7 specialized agents working together
2. **Closed-loop system**: Input → Analysis → Allocation → Action → Feedback → Re-plan
3. **Dynamic re-planning**: System adapts when disaster state changes (NOT static)
4. **Human-in-the-loop**: Critical decisions require approval
5. **Constraint-based optimization**: Real algorithm (OR-Tools), not random
6. **Complete audit trail**: Every action logged with reasoning
7. **Real integrations ready**: IMD, GDACS, MOSDAC adapters implemented (simulation mode for demo)

## Technical Highlights

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind
- **Backend**: FastAPI, PostgreSQL + PostGIS, Redis
- **Agents**: LangGraph orchestration, Claude/GPT-4
- **Optimization**: Google OR-Tools constraint solver
- **Geospatial**: PostGIS, distance calculations, ETA estimation

## Backup Talking Points

If questions arise:

**"Is this just a dashboard?"**
→ No - it's a closed-loop orchestration system. The agents make recommendations, the optimization is real, and the system dynamically re-plans.

**"Where's the AI?"**
→ LLM agents handle: situation analysis, duplicate detection, needs assessment, coordination task generation. Deterministic code handles: scoring, optimization, resource accounting.

**"Does this really re-plan?"**
→ Yes - submit the urgent update and watch priority scores change, re-planning trigger, and allocations shift in real-time.

**"Production ready?"**
→ This is a hackathon MVP demonstrating the core concept. Production would add: authentication, external API integrations, advanced routing, real-time notifications, multi-region support.

## Demo Reset (if needed)

```bash
# Backend
python scripts/reset_demo.py

# Or manually
psql -U postgres -d nexus_r -c "TRUNCATE incidents, needs, allocations, coordination_tasks, audit_events CASCADE;"
python scripts/seed_demo_data.py
```

## Likely Judge Questions

**Q: How do you prevent hallucination in critical scenarios?**
A: LLMs only handle interpretation and extraction. All calculations (priority scores, optimization, resource accounting) use deterministic code. Every allocation has explainable reasoning.

**Q: What happens if the LLM fails?**
A: System gracefully degrades - uses default confidence values and continues. Human operators see the low confidence and can intervene.

**Q: How does this scale?**
A: PostgreSQL + PostGIS handle geospatial queries efficiently. Agent orchestration is async. For production: horizontal scaling, message queue for agent tasks, caching layer.

**Q: Real-world deployment?**
A: Partner with NDMA/SDMA, integrate actual agency systems, deploy on government cloud, train operators, establish approval workflows, connect to existing communication channels.
