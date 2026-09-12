# PS20 Traceability

Internal mapping of CodeCommit product surfaces to PS20 requirements.

| PS20 requirement | Status | Evidence |
| --- | --- | --- |
| Incident / zone reporting | IMPLEMENTED | `POST /api/incidents`, `/incidents` |
| Resource inventory | IMPLEMENTED | `GET /api/resources`, `/resources` |
| Needs assessment | IMPLEMENTED | `NeedsCalculator` |
| Allocation / optimization | IMPLEMENTED | `ResourceOptimizer` OR-Tools |
| Inter-agency coordination | IMPLEMENTED | `/api/coordination/tasks`, `/coordination` |
| Dynamic re-allocation | IMPLEMENTED | inject urgent → replan + delta |
| Priority / severity | IMPLEMENTED | `PriorityCalculator` + UI breakdown |
| Duplicate-effort detection | IMPLEMENTED | heuristic hybrid |
| Coordination dashboard | IMPLEMENTED | `/coordination` |
| Activity / audit log | IMPLEMENTED | `/agents`, `/audit` |

## External integrations

| Integration | Status |
| --- | --- |
| IMD | SIMULATION / ADAPTER READY (live client documented; blocked without IMD_API_KEY) |
| GDACS | LIVE INTEGRATED (default SIMULATION; `GDACS_MODE=live` uses official Events API) |
| MOSDAC | ADAPTER READY / SIMULATION |
| Routing | SIMULATION (OSRM adapter if OSRM_BASE_URL set) |
| WebSockets | NOT IMPLEMENTED |
| SSE operational stream | IMPLEMENTED (`GET /api/events/stream`, polling fallback) |
| LangGraph | IMPLEMENTED (orchestrates existing incident steps; approval remains HTTP) |
| PostgreSQL/PostGIS default | PARTIALLY IMPLEMENTED (compose + schema; SQLite still the verified local demo) |
