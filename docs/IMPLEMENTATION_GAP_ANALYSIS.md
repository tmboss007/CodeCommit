# NEXUS-R Implementation Gap Analysis

**Source of truth:** repository source code (not README/IMPLEMENTATION.md).  
**Date:** 2026-09-11  
**Problem:** PS20 — Agentic Disaster Relief & Emergency Resource Coordinator

## Documentation contradictions

| Claim | Reality |
| --- | --- |
| PostgreSQL + PostGIS + Redis required | App runs on SQLite; Redis unused at runtime |
| LangGraph orchestration | Not imported or used |
| WebSockets for live dashboard | Not implemented (HTTP polling only) |
| MapLibre command-center map | Dependency listed; no map component or pages |
| Full command-center screens | Only `frontend/src/app/page.tsx` exists; `/incidents`, `/resources`, `/coordination` 404 |
| Human approval changes operational state | Approval flips task/allocation status only; resources stay `available` |
| Dynamic replan on new reports | `old_state` is hardcoded empty, so live replanning never compares real snapshots |
| IMD/GDACS/MOSDAC | No provider adapters |
| Simulation controls | No `/api/simulation/*` endpoints or UI |

## Requirement status

| Requirement | Status | Notes |
| --- | --- | --- |
| Incident / zone reporting | PARTIALLY IMPLEMENTED | POST `/api/incidents` exists; no zone selector UI; no dedicated incidents page |
| Resource inventory | PARTIALLY IMPLEMENTED | GET list only; no PATCH; SQLite seed has 6 resources (demo seed file has 12 but uses PostGIS) |
| Needs-assessment | IMPLEMENTED | Deterministic `NeedsCalculator` |
| Allocation / OR-Tools | PARTIALLY IMPLEMENTED | SCIP solver is used; does not constrain allocation ≤ unmet need; teams can be split |
| Inter-agency coordination | PARTIALLY IMPLEMENTED | Tasks generated; UI missing |
| Dynamic re-allocation | BROKEN | Replan endpoint regenerates a plan but does not compare prior state or produce a delta in the live path |
| Priority / severity | IMPLEMENTED | Weighted 0–100 with breakdown; breakdown not persisted or shown |
| Duplicate detection | PARTIALLY IMPLEMENTED | LLM-only; fails closed without API key; no POSSIBLE_DUPLICATE status |
| Coordination dashboard | MISSING | Linked from home, no route |
| Activity / audit log | PARTIALLY IMPLEMENTED | Events written; sparse agent names; no audit page |
| Human approval mutates state | PARTIALLY IMPLEMENTED | Does not move resources or write rich audit |
| Allocation delta UI | MISSING | `compute_allocation_delta` exists unused by API/UI |
| MapLibre map | MISSING | |
| Simulation engine | MISSING | |
| External adapters | MISSING | |
| WebSocket/SSE | MISSING | |
| 5-zone demo seed | PARTIALLY IMPLEMENTED | Zones exist; initial incidents/plan not loaded as a demo scenario |
| E2E closed-loop test | MISSING | Unit tests for priority/optimizer/replanner only |

## Priority order (implementation)

1. Persist operational snapshot and make replanning real (delta + auto-trigger).
2. Simulation API: reset, load demo, inject urgent Zone A report, disable resource, block route.
3. Approval must reserve/deploy resources and write audit events.
4. Heuristic situation + duplicate agents so the demo works without LLM keys (LLM optional).
5. Command-center UI: map, incidents, resources, coordination, audit, simulation, allocation delta.
6. Mock IMD/GDACS/MOSDAC/routing adapters labeled SIMULATION.
7. E2E test for the judge scenario.
