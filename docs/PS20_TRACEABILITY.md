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
| IMD | SIMULATED / ADAPTER READY |
| GDACS | SIMULATED / ADAPTER READY |
| MOSDAC | SIMULATED / ADAPTER READY |
| Routing | SIMULATED |
| WebSockets | NOT IMPLEMENTED (polling) |
| LangGraph | NOT IMPLEMENTED |
| PostgreSQL/PostGIS default | NOT USED (SQLite MVP) |
