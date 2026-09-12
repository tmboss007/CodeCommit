# LangGraph integration

Status: **IMPLEMENTED** (orchestration wrapper only). Approval, OR-Tools, SSE, and schema unchanged.

## Current flow (before / still the business path)

`OrchestrationService.process_incident_report` is the incident pipeline. It is not a graph; it is a Python method.

```text
INCIDENT_CREATED (audit + SSE, commits)
  → SituationAgent.analyze_report
  → DuplicateDetectionAgent.check_duplicate
  → INCIDENT_ANALYZED | DUPLICATE_DETECTED (commits)
  → persist Incident + Need rows
  → NeedsCalculator.calculate_needs
  → NEEDS_UPDATED (commits)
  → PriorityCalculator via _update_zone_priority
  → PRIORITY_CHANGED (commits)
  → db.commit()  # incident + needs + zone
  → ReplanningAgent.should_replan (+ 15-point priority override)
  → if auto_replan and replan_required:
        REPLAN_TRIGGERED
        generate_allocation_plan()
```

`generate_allocation_plan` (also used by load demo / manual replan / disable resource — **not** only the incident graph):

```text
supersede stale pending allocations/tasks
  → ALLOCATION_CREATED (commits)
  → ResourceOptimizer.optimize_allocation
  → persist pending Allocation rows
  → db.commit()
  → update Need fulfilled/remaining
  → CoordinationAgent.generate_tasks
  → delta / Plan(pending_approval) / ReplanningEvent
  → ALLOCATION_CHANGED (commits)
```

Human approval stays **outside** the graph:

- `POST /api/plans/{id}/approve` → `approve_plan`
- `POST /api/plans/{id}/reject` → `reject_plan`

Those methods keep their existing validation, single apply transaction, and `commit=False` audit batching.

## State object

`IncidentGraphState` (TypedDict) on `backend/app/services/incident_graph.py`.

| Key | Role |
|-----|------|
| `orchestrator` | `OrchestrationService` (request-scoped; not checkpointed) |
| `report_text`, `source`, `zone_id`, `correlation_id`, `auto_replan` | inputs |
| `old_snapshot` | pre-report zone/resource snapshot for replan |
| `structured_incident` | situation analysis dict |
| `duplicate_result` | duplicate check dict |
| `incident_id`, `needs` | persisted after needs/priority commit |
| `priority`, `priority_breakdown`, `old_priority` | zone scores |
| `replan_required`, `replanning_reason`, `replan_details` | evaluator |
| `optimization_result` | first half of `generate_allocation_plan` |
| `current_plan`, `coordination_tasks` | pending plan payload |
| `errors` | node failures |

No LangGraph checkpointer. No Redis.

## Nodes (wrappers only)

| Node | Existing functions |
|------|-------------------|
| `situation` | `SituationAgent.analyze_report`, `_log_event(INCIDENT_CREATED)` |
| `duplicate` | `DuplicateDetectionAgent.check_duplicate`, `_log_event` |
| `needs` | `NeedsCalculator.calculate_needs`, `Incident`/`Need` add |
| `priority` | `_update_zone_priority`, `_log_event(PRIORITY_CHANGED)`, **same `db.commit()` as before** |
| `replanning` | `ReplanningAgent.should_replan` + 15-point override; `REPLAN_TRIGGERED` if continuing |
| `optimization` | `_optimization_step` (optimizer + pending allocations) |
| `coordination` | `_coordination_step` (tasks, delta, Plan row) |

`generate_allocation_plan` remains a public API: `_optimization_step` then `_coordination_step`. Load-demo / run-replan do not go through the incident graph.

## Graph

```text
START → situation → duplicate → needs → priority → replanning
                                                      │
                         errors or not (replan and auto_replan)
                                                      ├─ END (keep current approved plan)
                                                      └─ optimization → coordination → END
                                                              (pending_approval plan)
```

## Transactions

Unchanged boundaries:

1. Per `_log_event(..., commit=True)` (existing).
2. After priority: one commit of incident/needs/zone.
3. Inside optimization: pending allocations.
4. Inside coordination: tasks + plan + delta.

Nodes do **not** add extra commits. Approval is not a graph node.

If a node raises: rollback the session, clear unpublished SSE, record `errors`, skip optimization so a plan is not half-applied. Incident rows already committed before replanning stay (same as the old method if `generate_allocation_plan` failed after the priority commit).

## SSE

Still: `AuditEvent` → `events_from_audit` → `EventBus` after successful commit.

Optional extra named events from the **same** audit row (not a second bus):

- `agent.situation.completed`
- `agent.duplicate.completed`
- `agent.needs.completed`
- `agent.priority.completed`
- `agent.replanning.triggered`
- `agent.optimization.completed`
- `agent.coordination.completed`

## What we will not do

- Rewrite agents as LLM graph nodes
- Move `approve_plan` into LangGraph
- Change OR-Tools, schema, or SSE transport
- Add checkpointing, Redis, or WebSockets
