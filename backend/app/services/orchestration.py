from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from app.models import (
    Zone, Incident, Need, Resource, Allocation, CoordinationTask, AuditEvent,
    AppState, ReplanningEvent, Agency, Plan,
)
from app.agents.core import SituationAgent, DuplicateDetectionAgent, CoordinationAgent
from app.agents.replanning import ReplanningAgent
from app.services.priority import PriorityCalculator, NeedsCalculator, calculate_distance_km
from app.services.optimizer import ResourceOptimizer, EXCLUSIVE_TYPES
from app.core.database import Base, engine
from app.services.demo_seed import seed_base_entities, INITIAL_REPORTS, URGENT_ZONE_A_REPORT
from app.services.incident_graph import run_incident_pipeline

ALLOCATABLE = {"available"}


class OrchestrationService:
    def __init__(self, db: Session):
        self.db = db
        self.situation_agent = SituationAgent()
        self.duplicate_agent = DuplicateDetectionAgent()
        self.coordination_agent = CoordinationAgent()
        self.replanning_agent = ReplanningAgent()
        self.optimizer = ResourceOptimizer()
        self._pending_events = []

    def _get_state(self) -> AppState:
        state = self.db.query(AppState).filter(AppState.id == "singleton").first()
        if not state:
            state = AppState(id="singleton", blocked_routes=[], last_snapshot={"zones": [], "resources": []}, data_mode="SIMULATION")
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

    def abort_pipeline(self):
        self.db.rollback()
        self._pending_events.clear()

    def situation_step(self, report_text: str, source: str, zone_id: Optional[str], correlation_id: str) -> Dict:
        self._log_event(
            "INCIDENT_CREATED",
            "Situation Agent received a new report",
            agent="Situation Agent",
            correlation_id=correlation_id,
            new_state={"source": source},
        )
        situation_result = self.situation_agent.analyze_report(report_text, zone_id)
        situation_result["zone_id"] = situation_result.get("zone_id") or zone_id or "ZONE_A"
        return situation_result

    def duplicate_step(self, report_text: str, structured: Dict, correlation_id: str) -> Dict:
        resolved_zone = structured.get("zone_id") or "ZONE_A"
        existing_incidents = self.db.query(Incident).filter(
            Incident.zone_id == resolved_zone,
            Incident.status == "active",
        ).all()
        duplicate_result = self.duplicate_agent.check_duplicate(
            report_text,
            [{"id": i.id, "zone_id": i.zone_id, "incident_type": i.incident_type,
              "timestamp": i.timestamp, "report_text": i.report_text} for i in existing_incidents],
            zone_id=resolved_zone,
            incident_type=structured.get("incident_type") or "other",
        )
        self._log_event(
            "DUPLICATE_DETECTED" if duplicate_result.get("is_duplicate") else "INCIDENT_ANALYZED",
            duplicate_result.get("explanation") or "Duplicate Agent evaluated overlap",
            agent="Duplicate Agent",
            correlation_id=correlation_id,
            new_state=duplicate_result,
        )
        return duplicate_result

    def needs_step(self, report_text: str, source: str, structured: Dict, duplicate_result: Dict, correlation_id: str):
        affected = structured.get("affected_population")
        if affected is None:
            affected = 400
            structured["affected_population"] = affected
            structured["population_estimated"] = True
        vulnerable = structured.get("vulnerable_population")
        if vulnerable is None:
            vulnerable = int(affected * 0.16)
            structured["vulnerable_population"] = vulnerable
        incident = Incident(
            id=f"inc_{uuid.uuid4().hex[:8]}",
            zone_id=structured.get("zone_id") or "ZONE_A",
            source=source,
            report_text=report_text,
            incident_type=structured.get("incident_type"),
            affected_population=affected,
            vulnerable_population=vulnerable,
            confidence=structured.get("confidence"),
            status="active",
            duplicate_group_id=(duplicate_result.get("matched_incidents") or [None])[0],
            duplicate_status=duplicate_result.get("duplicate_status") or "NEW",
            analysis_result=structured,
        )
        self.db.add(incident)
        needs_list = NeedsCalculator.calculate_needs(
            affected,
            vulnerable,
            structured.get("incident_type", "other"),
            structured.get("severity", 5.0),
        )
        for need in needs_list:
            self.db.add(Need(
                id=f"need_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                zone_id=incident.zone_id,
                resource_type=need["type"],
                quantity_required=need["quantity"],
                quantity_remaining=need["quantity"],
                urgency=need["urgency"],
                unit=need.get("unit"),
            ))
        water = next((n for n in needs_list if n["type"] == "water_liter"), None)
        self._log_event(
            "NEEDS_UPDATED",
            f"Needs Service calculated requirements for {incident.zone_id}"
            + (f". Water required: {water['quantity']} L" if water else ""),
            agent="Needs Service",
            correlation_id=correlation_id,
            new_state={"needs": needs_list},
        )
        return incident.id, needs_list

    def priority_step(self, incident_id: str, correlation_id: str):
        incident = self.db.query(Incident).filter(Incident.id == incident_id).first()
        zone = self.db.query(Zone).filter(Zone.id == incident.zone_id).first() if incident else None
        old_priority = zone.priority_score if zone else None
        if zone and incident:
            self._update_zone_priority(zone, incident)
            self._log_event(
                "PRIORITY_CHANGED",
                f"Priority Service {zone.id}: {old_priority:.0f} → {zone.priority_score:.0f}",
                agent="Priority Service",
                correlation_id=correlation_id,
                previous_state={"priority": old_priority},
                new_state={"priority": zone.priority_score, "breakdown": zone.priority_breakdown},
            )
        self.db.commit()
        return (zone.priority_score if zone else None), (zone.priority_breakdown if zone else None), old_priority

    def replanning_step(self, old_snapshot: Dict, old_priority, incident_id: str, auto_replan: bool, correlation_id: str):
        incident = self.db.query(Incident).filter(Incident.id == incident_id).first()
        zone = self.db.query(Zone).filter(Zone.id == incident.zone_id).first() if incident else None
        should_replan, reason, details = self.replanning_agent.should_replan(
            old_snapshot,
            self._current_snapshot(),
            self._allocation_dicts(status="approved"),
        )
        if not should_replan and old_priority is not None and zone and abs(zone.priority_score - old_priority) >= 15:
            should_replan = True
            reason = f"Zone {zone.id} priority change: {old_priority:.0f} → {zone.priority_score:.0f}"
            details = {"priority_changes": [{"zone_id": zone.id, "old_priority": old_priority, "new_priority": zone.priority_score}]}
        if auto_replan and should_replan:
            self._log_event(
                "REPLAN_TRIGGERED",
                f"Replanning Evaluator: {reason}",
                agent="Replanning Evaluator",
                correlation_id=correlation_id,
                new_state=details,
            )
        return should_replan, reason, details

    def process_incident_report(
        self,
        report_text: str,
        source: str,
        zone_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        auto_replan: bool = True,
    ) -> Dict:
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
        try:
            out = run_incident_pipeline(
                self,
                report_text=report_text,
                source=source,
                zone_id=zone_id,
                correlation_id=correlation_id,
                auto_replan=auto_replan,
            )
        except Exception as exc:
            self.abort_pipeline()
            return {
                "error": "pipeline_failed",
                "details": [str(exc)],
                "correlation_id": correlation_id,
                "plan": None,
                "replanning_required": False,
            }
        structured = out.get("structured_incident") or {}
        if out.get("errors"):
            return {
                "error": "pipeline_failed",
                "details": out["errors"],
                "correlation_id": correlation_id,
                "incident_id": out.get("incident_id"),
                "zone_id": structured.get("zone_id") or zone_id,
                "replanning_required": False,
                "plan": None,
            }
        return {
            "incident_id": out.get("incident_id"),
            "zone_id": structured.get("zone_id") or zone_id,
            "situation_analysis": structured,
            "duplicate_check": out.get("duplicate_result"),
            "needs_created": out.get("needs_created") or 0,
            "needs": out.get("needs_list") or [],
            "zone_priority_updated": out.get("zone_priority"),
            "priority_breakdown": out.get("priority_breakdown"),
            "replanning_required": out.get("replan_required"),
            "replanning_reason": out.get("replanning_reason"),
            "correlation_id": correlation_id,
            "plan": out.get("current_plan"),
        }

    def ingest_external_event(self, event: Dict, auto_replan: bool = True) -> Dict:
        """Map a normalized provider event onto the existing incident pipeline."""
        loc = event.get("location") or {}
        zone_id = self._nearest_zone_id(loc.get("lat"), loc.get("lon"))
        source = event.get("source") or "external"
        title = event.get("title") or event.get("event_type") or "External event"
        alert = event.get("alert_level") or ""
        report = f"{source} {alert} {event.get('event_type') or 'event'}: {title}."
        if loc.get("country"):
            report += f" Country: {loc.get('country')}."
        result = self.process_incident_report(
            report_text=report,
            source=source,
            zone_id=zone_id,
            auto_replan=auto_replan,
        )
        result["provider_event"] = {
            "source": source,
            "data_mode": event.get("data_mode"),
            "event_time": event.get("event_time"),
            "fetched_at": event.get("fetched_at"),
            "external_id": event.get("external_id"),
        }
        return result

    def _nearest_zone_id(self, lat, lon) -> str:
        from app.core.spatial import nearest_zone_id
        return nearest_zone_id(self.db, lat, lon)

    def generate_allocation_plan(
        self,
        correlation_id: Optional[str] = None,
        trigger: str = "manual",
        prior_snapshot: Optional[Dict] = None,
    ) -> Dict:
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
        packed = self.optimization_step(correlation_id=correlation_id, trigger=trigger, prior_snapshot=prior_snapshot)
        return self.coordination_step(packed)

    def optimization_step(self, correlation_id: str, trigger: str = "manual", prior_snapshot: Optional[Dict] = None) -> Dict:
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        app_state = self._get_state()
        previous_plan_id = app_state.active_plan_id
        prior_snapshot = prior_snapshot or self._current_snapshot()
        old_allocations = self._allocation_dicts()

        pending = self.db.query(Allocation).filter(Allocation.status == "pending").all()
        for alloc in pending:
            alloc.status = "superseded"
            stale_tasks = self.db.query(CoordinationTask).filter(
                CoordinationTask.allocation_id == alloc.id,
                CoordinationTask.status == "pending",
            ).all()
            for task in stale_tasks:
                task.status = "superseded"

        self._log_event(
            "ALLOCATION_CREATED",
            "Optimization Engine generating allocation",
            agent="Optimization Engine",
            correlation_id=correlation_id,
        )

        zones = self.db.query(Zone).filter(Zone.status == "active").all()
        zones_data = [self._zone_to_dict(z) for z in zones]
        resources = self.db.query(Resource).all()
        resources_data = [self._resource_to_dict(r) for r in resources]
        needs_by_zone = self._get_needs_by_zone()
        distances = self._calculate_distances(resources_data, zones_data, app_state.blocked_routes or [])

        allocations, unmet_demands, explanation = self.optimizer.optimize_allocation(
            zones_data, resources_data, needs_by_zone, distances
        )

        for alloc in allocations:
            resource = self.db.query(Resource).filter(Resource.id == alloc["resource_id"]).first()
            from_zone = resource.current_zone_id if resource else None
            alloc["from_zone_id"] = from_zone
            self.db.add(Allocation(
                id=alloc["id"],
                resource_id=alloc["resource_id"],
                zone_id=alloc["zone_id"],
                quantity=alloc.get("quantity"),
                priority=alloc.get("priority"),
                eta_minutes=alloc.get("eta_minutes"),
                reason=alloc.get("reason"),
                status="pending",
                plan_id=plan_id,
                from_zone_id=from_zone,
            ))

        self.db.commit()
        return {
            "plan_id": plan_id,
            "correlation_id": correlation_id,
            "trigger": trigger,
            "previous_plan_id": previous_plan_id,
            "prior_snapshot": prior_snapshot,
            "old_allocations": old_allocations,
            "allocations": allocations,
            "unmet_demands": unmet_demands,
            "explanation": explanation,
            "resources_data": resources_data,
            "zones_data": zones_data,
        }

    def coordination_step(self, packed: Dict) -> Dict:
        plan_id = packed["plan_id"]
        correlation_id = packed["correlation_id"]
        trigger = packed["trigger"]
        previous_plan_id = packed["previous_plan_id"]
        prior_snapshot = packed["prior_snapshot"]
        old_allocations = packed["old_allocations"]
        allocations = packed["allocations"]
        unmet_demands = packed["unmet_demands"]
        explanation = packed["explanation"]
        resources_data = packed["resources_data"]
        zones_data = packed["zones_data"]
        app_state = self._get_state()

        fulfilled_by_zone_type: Dict[str, Dict[str, float]] = {}
        resources_by_id = {r.id: r for r in self.db.query(Resource).all()}
        for alloc in allocations:
            res = resources_by_id.get(alloc["resource_id"])
            if not res:
                continue
            fulfilled_by_zone_type.setdefault(alloc["zone_id"], {})
            fulfilled_by_zone_type[alloc["zone_id"]][res.type] = (
                fulfilled_by_zone_type[alloc["zone_id"]].get(res.type, 0) + (alloc.get("quantity") or 0)
            )
        for need in self.db.query(Need).all():
            got = fulfilled_by_zone_type.get(need.zone_id, {}).get(need.resource_type, 0)
            need.quantity_fulfilled = min(got, need.quantity_required or 0)
            need.quantity_remaining = max(0, (need.quantity_required or 0) - (need.quantity_fulfilled or 0))

        resources_map = {r["id"]: r for r in resources_data}
        zones_map = {z["id"]: z for z in zones_data}
        agencies = {a.id: {"id": a.id, "name": a.name} for a in self.db.query(Agency).all()}
        tasks = self.coordination_agent.generate_tasks(allocations, resources_map, zones_map, agencies)
        task_objs = []
        for task in tasks:
            obj = CoordinationTask(
                id=f"task_{uuid.uuid4().hex[:8]}",
                agency_id=task["agency_id"],
                allocation_id=task.get("allocation_id"),
                plan_id=plan_id,
                action=task["action"],
                status="pending",
            )
            self.db.add(obj)
            task_objs.append(obj)

        delta = self.replanning_agent.compute_allocation_delta(old_allocations, allocations)
        delta["before_by_zone"] = self._counts_by_zone(old_allocations)
        delta["after_by_zone"] = self._counts_by_zone(allocations)
        delta["moves"] = self._moves(old_allocations, allocations, resources_map)
        old_zone_map = {z["id"]: z for z in prior_snapshot.get("zones", [])}
        delta["priority_changes"] = []
        for z in self.db.query(Zone).filter(Zone.status == "active").all():
            old_p = old_zone_map.get(z.id, {}).get("priority_score")
            if old_p is not None and abs((z.priority_score or 0) - old_p) >= 0.01:
                delta["priority_changes"].append({
                    "zone_id": z.id,
                    "before": old_p,
                    "after": z.priority_score,
                })

        app_state.last_plan_id = plan_id
        app_state.last_plan_status = "pending"
        app_state.last_plan_trigger = trigger
        app_state.last_snapshot = self._current_snapshot()
        app_state.last_delta = delta
        app_state.last_unmet = unmet_demands
        app_state.last_explanation = explanation
        app_state.updated_at = datetime.utcnow()

        self.db.add(Plan(
            id=plan_id,
            status="pending_approval",
            trigger=trigger,
            previous_plan_id=previous_plan_id,
        ))
        self.db.add(ReplanningEvent(
            id=f"replan_{uuid.uuid4().hex[:8]}",
            trigger=trigger,
            old_plan_id=previous_plan_id,
            new_plan_id=plan_id,
            changed_zones=list({a["zone_id"] for a in allocations}),
            changed_resources=list({a["resource_id"] for a in allocations}),
            delta=delta,
            correlation_id=correlation_id,
        ))

        self._log_event(
            "ALLOCATION_CHANGED",
            f"Coordination Agent created {len(task_objs)} agency tasks. {delta.get('summary')}",
            agent="Coordination Agent",
            correlation_id=correlation_id,
            new_state={"plan_id": plan_id, "delta": delta},
        )
        self.db.commit()

        return {
            "plan_id": plan_id,
            "allocations": allocations,
            "unmet_demands": unmet_demands,
            "coordination_tasks": [
                {"id": t.id, "agency_id": t.agency_id, "action": t.action, "status": t.status, "allocation_id": t.allocation_id}
                for t in task_objs
            ],
            "explanation": explanation,
            "delta": delta,
            "trigger": trigger,
            "previous_plan_id": previous_plan_id,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
        }

    def approve_task(self, task_id: str, actor: str = "operator") -> Dict:
        task = self.db.query(CoordinationTask).filter(CoordinationTask.id == task_id).first()
        if not task:
            return {"error": "not_found"}
        previous = {"task_status": task.status}
        task.status = "approved"
        task.approved_at = datetime.utcnow()
        allocation = None
        if task.allocation_id:
            allocation = self.db.query(Allocation).filter(Allocation.id == task.allocation_id).first()
            if allocation:
                allocation.status = "approved"
                allocation.approved_at = datetime.utcnow()
                allocation.approved_by = actor
                resource = self.db.query(Resource).filter(Resource.id == allocation.resource_id).first()
                if resource:
                    resource.status = "en_route" if resource.type in EXCLUSIVE_TYPES else "reserved"
                    resource.current_zone_id = allocation.zone_id
                    resource.eta_minutes = allocation.eta_minutes
        self._log_event(
            "APPROVAL_GRANTED",
            f"Human Approval granted for {task_id}",
            actor=actor,
            agent="Human Approval",
            previous_state=previous,
            new_state={"task_id": task_id, "allocation_id": task.allocation_id, "resource_status": allocation and "updated"},
            correlation_id=None,
        )
        self.db.commit()
        return {"status": "approved", "task_id": task_id}

    def reject_task(self, task_id: str, actor: str = "operator") -> Dict:
        task = self.db.query(CoordinationTask).filter(CoordinationTask.id == task_id).first()
        if not task:
            return {"error": "not_found"}
        previous = {"task_status": task.status}
        task.status = "rejected"
        if task.allocation_id:
            allocation = self.db.query(Allocation).filter(Allocation.id == task.allocation_id).first()
            if allocation:
                allocation.status = "rejected"
        self._log_event(
            "APPROVAL_REJECTED",
            f"Human Approval rejected {task_id}. Allocation unchanged for deployment.",
            actor=actor,
            agent="Human Approval",
            previous_state=previous,
            new_state={"task_id": task_id},
        )
        self.db.commit()
        return {"status": "rejected", "task_id": task_id}

    def revise_plan_card(self, plan_id: Optional[str] = None) -> Optional[Dict]:
        state = self._get_state()
        plan_id = plan_id or state.last_plan_id
        if not plan_id:
            return None
        allocations = self.db.query(Allocation).filter(Allocation.plan_id == plan_id).all()
        pending_allocs = [a for a in allocations if a.status == "pending"]
        if state.last_plan_status != "pending" or not pending_allocs:
            return {
                "plan_id": plan_id,
                "status": state.last_plan_status or "none",
                "pending": False,
            }
        resources = {r.id: r for r in self.db.query(Resource).all()}
        tasks = []
        for alloc in pending_allocs:
            tasks.extend(self.db.query(CoordinationTask).filter(CoordinationTask.allocation_id == alloc.id).all())
        agencies = sorted({t.agency_id for t in tasks})
        affected_zones = sorted({a.zone_id for a in pending_allocs})
        delta = state.last_delta or {}
        moves = delta.get("moves") or []
        priority_changes = []
        for change in delta.get("priority_changes") or []:
            before = change.get("before")
            after = change.get("after")
            if before is None or after is None:
                continue
            if abs(float(after) - float(before)) >= 0.01:
                priority_changes.append(change)
        trigger = state.last_plan_trigger or "state_change"
        trigger_label = "Urgent Incident / State Change"
        if trigger == "load_demo":
            trigger_label = "Initial scenario"
        elif trigger == "manual_replan":
            trigger_label = "Manual replan"
        before_lines = []
        after_lines = []
        for alloc in pending_allocs:
            res = resources.get(alloc.resource_id)
            name = res.name if res else alloc.resource_id
            if alloc.from_zone_id:
                before_lines.append(f"{alloc.from_zone_id} → {name}")
            after_lines.append(f"{alloc.zone_id} → {name}")
        for move in moves:
            if move.get("from_zone") and move.get("name"):
                line = f"{move['from_zone']} → {move['name']}"
                if line not in before_lines:
                    before_lines.append(line)
                after_lines.append(f"{move.get('to_zone')} → {move.get('name')}")
        return {
            "plan_id": plan_id,
            "status": "pending",
            "pending": True,
            "trigger": trigger,
            "trigger_label": trigger_label,
            "affected_zones": affected_zones,
            "resources_to_move": len(moves) or len(pending_allocs),
            "agencies_affected": len(agencies),
            "agencies": agencies,
            "priority_changes": priority_changes,
            "estimated_impact": state.last_explanation or delta.get("summary"),
            "pending_task_count": len(tasks),
            "pending_allocation_count": len(pending_allocs),
            "delta": delta,
            "review": {
                "before": before_lines[:40],
                "after": after_lines[:40],
                "total_movements": len(moves) or len(pending_allocs),
                "affected_agencies": len(agencies),
                "priority_changes": priority_changes,
            },
        }

    def approve_plan(self, plan_id: str, actor: str = "operator") -> Dict:
        state = self._get_state()
        if not plan_id:
            return {"error": "missing_plan", "status_code": 404}
        if state.last_plan_id == plan_id and state.last_plan_status == "approved":
            return {"error": "already_approved", "status_code": 409}

        allocations = self.db.query(Allocation).filter(
            Allocation.plan_id == plan_id,
            Allocation.status == "pending",
        ).all()
        if not allocations:
            already = self.db.query(Allocation).filter(Allocation.plan_id == plan_id, Allocation.status == "approved").count()
            if already:
                return {"error": "already_approved", "status_code": 409}
            return {"error": "plan_not_found", "status_code": 404}

        errors = self._validate_plan_allocations(allocations)
        if errors:
            return {"error": "validation_failed", "details": errors, "status_code": 400}

        previous_active = state.active_plan_id
        now = datetime.utcnow()
        resource_ids = []
        task_ids = []
        try:
            for alloc in allocations:
                resource = self.db.query(Resource).filter(Resource.id == alloc.resource_id).first()
                if not resource:
                    raise RuntimeError("resource_missing_during_apply")
                prior_allocs = self.db.query(Allocation).filter(
                    Allocation.resource_id == alloc.resource_id,
                    Allocation.status == "approved",
                    Allocation.id != alloc.id,
                ).all()
                for old in prior_allocs:
                    old.status = "superseded"
                alloc.status = "approved"
                alloc.approved_at = now
                alloc.approved_by = actor
                resource.status = "en_route" if resource.type in EXCLUSIVE_TYPES else "reserved"
                resource.current_zone_id = alloc.zone_id
                resource.eta_minutes = alloc.eta_minutes
                resource_ids.append(resource.id)
                tasks = self.db.query(CoordinationTask).filter(CoordinationTask.allocation_id == alloc.id).all()
                for task in tasks:
                    task.status = "approved"
                    task.approved_at = now
                    task_ids.append(task.id)
                    self._log_event(
                        "APPROVAL_GRANTED",
                        f"Human Approval granted for {task.id} as part of plan {plan_id}",
                        actor=actor,
                        agent="Human Approval",
                        new_state={"task_id": task.id, "allocation_id": alloc.id, "plan_id": plan_id},
                        correlation_id=plan_id,
                        commit=False,
                    )
            if previous_active and previous_active != plan_id:
                self._supersede_plan(previous_active)
            plan_row = self.db.query(Plan).filter(Plan.id == plan_id).first()
            if plan_row:
                plan_row.status = "active"
                plan_row.approved_at = now
            state.last_plan_status = "approved"
            state.last_plan_id = plan_id
            state.active_plan_id = plan_id
            self._log_event(
                "PLAN_APPROVED",
                f"Revised response plan {plan_id} approved ({len(task_ids)} tasks, {len(allocations)} allocations)",
                actor=actor,
                agent="Human Approval",
                previous_state={"active_plan_id": previous_active},
                new_state={"plan_id": plan_id, "tasks": task_ids, "resources": resource_ids},
                correlation_id=plan_id,
                commit=False,
            )
            self.db.commit()
            self._emit_pending()
        except Exception as exc:
            self.db.rollback()
            self._pending_events.clear()
            return {"error": "apply_failed", "details": [str(exc)], "status_code": 500}

        return {
            "status": "approved",
            "plan_id": plan_id,
            "active_plan_id": plan_id,
            "previous_plan_id": previous_active,
            "tasks_approved": len(task_ids),
            "allocations_approved": len(allocations),
            "resources_updated": len(set(resource_ids)),
        }

    def reject_plan(self, plan_id: str, actor: str = "operator") -> Dict:
        state = self._get_state()
        allocations = self.db.query(Allocation).filter(
            Allocation.plan_id == plan_id,
            Allocation.status == "pending",
        ).all()
        if not allocations:
            if state.last_plan_id == plan_id and state.last_plan_status == "rejected":
                return {"error": "already_rejected", "status_code": 409}
            return {"error": "plan_not_found", "status_code": 404}

        previous_active = state.active_plan_id
        task_ids = []
        for alloc in allocations:
            alloc.status = "rejected"
            tasks = self.db.query(CoordinationTask).filter(CoordinationTask.allocation_id == alloc.id).all()
            for task in tasks:
                task.status = "rejected"
                task_ids.append(task.id)
        plan_row = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if plan_row:
            plan_row.status = "rejected"
            plan_row.rejected_at = datetime.utcnow()
        state.last_plan_status = "rejected"
        self._log_event(
            "PLAN_REJECTED",
            f"Revised response plan {plan_id} rejected. Previous active plan preserved.",
            actor=actor,
            agent="Human Approval",
            previous_state={"active_plan_id": previous_active},
            new_state={"plan_id": plan_id, "tasks_rejected": task_ids},
            correlation_id=plan_id,
            commit=False,
        )
        self.db.commit()
        self._emit_pending()
        return {
            "status": "rejected",
            "plan_id": plan_id,
            "tasks_rejected": len(task_ids),
            "active_plan_id": previous_active,
        }

    def _validate_plan_allocations(self, allocations) -> list:
        errors = []
        seen_exclusive = {}
        for alloc in allocations:
            resource = self.db.query(Resource).filter(Resource.id == alloc.resource_id).first()
            if not resource:
                errors.append(f"Resource {alloc.resource_id} no longer exists")
                continue
            if resource.status in ("unavailable", "maintenance"):
                errors.append(f"Resource {resource.id} is {resource.status} and cannot be allocated")
            if alloc.quantity and resource.quantity is not None and alloc.quantity > resource.quantity + 0.001:
                errors.append(f"Resource {resource.id} over-allocated ({alloc.quantity} > {resource.quantity})")
            zone = self.db.query(Zone).filter(Zone.id == alloc.zone_id).first()
            if not zone:
                errors.append(f"Zone {alloc.zone_id} is invalid")
            if resource.type in EXCLUSIVE_TYPES:
                if resource.id in seen_exclusive and seen_exclusive[resource.id] != alloc.zone_id:
                    errors.append(f"Exclusive resource {resource.id} assigned to conflicting zones")
                seen_exclusive[resource.id] = alloc.zone_id
        return errors

    def _supersede_plan(self, plan_id: str):
        plan_row = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if plan_row and plan_row.status == "active":
            plan_row.status = "superseded"
        allocs = self.db.query(Allocation).filter(
            Allocation.plan_id == plan_id,
            Allocation.status == "approved",
        ).all()
        for alloc in allocs:
            alloc.status = "superseded"
            tasks = self.db.query(CoordinationTask).filter(CoordinationTask.allocation_id == alloc.id).all()
            for task in tasks:
                if task.status in ("approved", "in_progress", "pending"):
                    task.status = "superseded"

    def list_plans(self) -> list:
        rows = self.db.query(Plan).order_by(Plan.created_at.desc()).all()
        return [
            {
                "id": p.id,
                "status": p.status,
                "trigger": p.trigger,
                "previous_plan_id": p.previous_plan_id,
                "created_at": p.created_at,
                "approved_at": p.approved_at,
                "rejected_at": p.rejected_at,
            }
            for p in rows
        ]

    def active_plan_tasks(self):
        state = self._get_state()
        if not state.active_plan_id:
            return []
        return self.db.query(CoordinationTask).filter(
            CoordinationTask.plan_id == state.active_plan_id,
            CoordinationTask.status.in_(["approved", "in_progress"]),
        ).all()

    ALLOWED_RESOURCE_STATUSES = {"available", "reserved", "en_route", "deployed", "unavailable", "maintenance"}

    def update_resource(
        self,
        resource_id: str,
        fields: Dict,
        actor: str = "operator",
        reason: Optional[str] = None,
    ) -> Dict:
        resource = self.db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            return {"error": "not_found", "status_code": 404}
        previous = {
            "status": resource.status,
            "current_zone_id": resource.current_zone_id,
            "eta_minutes": resource.eta_minutes,
        }
        if "status" in fields and fields["status"] is not None:
            status = str(fields["status"]).strip().lower()
            if status not in self.ALLOWED_RESOURCE_STATUSES:
                return {"error": "invalid_status", "status_code": 400, "details": [f"Status {fields['status']} is not allowed"]}
            resource.status = status
        if "current_zone_id" in fields:
            zone_id = fields["current_zone_id"]
            if zone_id in (None, "", "none", "unassigned"):
                resource.current_zone_id = None
            else:
                zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
                if not zone:
                    return {"error": "invalid_zone", "status_code": 400, "details": [f"Zone {zone_id} is invalid"]}
                resource.current_zone_id = zone_id
        if "eta_minutes" in fields:
            eta = fields["eta_minutes"]
            if eta is None or eta == "":
                resource.eta_minutes = None
            else:
                try:
                    resource.eta_minutes = int(eta)
                except (TypeError, ValueError):
                    return {"error": "invalid_eta", "status_code": 400, "details": ["ETA must be an integer number of minutes"]}
                if resource.eta_minutes < 0:
                    return {"error": "invalid_eta", "status_code": 400, "details": ["ETA cannot be negative"]}
        new_state = {
            "status": resource.status,
            "current_zone_id": resource.current_zone_id,
            "eta_minutes": resource.eta_minutes,
        }
        corr = f"corr_manual_{uuid.uuid4().hex[:8]}"
        note = reason or "Manual inventory correction"
        self._log_event(
            "RESOURCE_STATE_CHANGED",
            f"Resource {resource.agency_id}-{resource.id} {previous['status']}/{previous['current_zone_id'] or 'unassigned'} → {new_state['status']}/{new_state['current_zone_id'] or 'unassigned'}",
            actor=actor,
            agent="Operator",
            previous_state=previous,
            new_state=new_state,
            correlation_id=corr,
            reason=note,
        )
        # _log_event already commits by default
        return {
            "id": resource.id,
            "status": resource.status,
            "current_zone_id": resource.current_zone_id,
            "eta_minutes": resource.eta_minutes,
            "correlation_id": corr,
            "reason": note,
        }

    def reset_world(self):
        seed_base_entities(self.db)
        self._get_state()
        self._log_event("RESOURCE_STATE_CHANGED", "Simulation reset to empty seeded inventory", agent="Simulation Engine")
        self.db.commit()
        self._emit_pending()
        self._publish_scenario("RESET")
        return {"status": "reset"}

    def load_demo(self) -> Dict:
        seed_base_entities(self.db)
        self._get_state()
        correlation_id = f"corr_{uuid.uuid4().hex[:8]}"
        reports = []
        for item in INITIAL_REPORTS:
            reports.append(self.process_incident_report(
                item["text"], item["source"], zone_id=item["zone_id"],
                correlation_id=correlation_id, auto_replan=False,
            ))
        plan = self.generate_allocation_plan(correlation_id=correlation_id, trigger="load_demo")
        self._publish_scenario("LOAD SCENARIO", correlation_id=correlation_id, extra={"plan_id": plan.get("plan_id")})
        return {"status": "loaded", "reports": reports, "plan": plan, "correlation_id": correlation_id}

    def inject_urgent_zone_a(self) -> Dict:
        state = self._get_state()
        blocked = list(state.blocked_routes or [])
        blocked.append({"zone_id": "ZONE_A", "reason": "two rescue routes inaccessible", "blocked": False})
        state.blocked_routes = blocked
        self.db.commit()
        self._emit_pending()
        result = self.process_incident_report(
            URGENT_ZONE_A_REPORT,
            source="simulation",
            zone_id="ZONE_A",
            auto_replan=True,
        )
        self._publish_scenario("INJECT URGENT REPORT", extra={"zone_id": "ZONE_A"})
        return result

    def disable_resource(self, resource_id: str) -> Dict:
        old = self._current_snapshot()
        resource = self.db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            return {"error": "not_found"}
        prev = resource.status
        resource.status = "unavailable"
        self._log_event(
            "RESOURCE_STATE_CHANGED",
            f"Resource {resource_id} disabled ({prev} → unavailable)",
            agent="Simulation Engine",
            previous_state={"status": prev},
            new_state={"status": "unavailable"},
        )
        self.db.commit()
        self._emit_pending()
        should, reason, details = self.replanning_agent.should_replan(old, self._current_snapshot(), self._allocation_dicts())
        plan = None
        if should:
            plan = self.generate_allocation_plan(trigger=reason)
        self._publish_scenario("DISABLE RESOURCE", extra={"resource_id": resource_id})
        return {"resource_id": resource_id, "status": "unavailable", "replanning_required": should, "plan": plan}

    def block_route(self, zone_id: str = "ZONE_A") -> Dict:
        state = self._get_state()
        blocked = list(state.blocked_routes or [])
        blocked.append({"zone_id": zone_id, "blocked": True, "reason": "route blocked by simulation"})
        state.blocked_routes = blocked
        self._log_event("RESOURCE_STATE_CHANGED", f"Route into {zone_id} blocked", agent="Simulation Engine")
        self.db.commit()
        self._emit_pending()
        plan = self.generate_allocation_plan(trigger=f"Route to {zone_id} unavailable")
        self._publish_scenario("BLOCK ROUTE", extra={"zone_id": zone_id, "plan_id": plan.get("plan_id")})
        return {"blocked": zone_id, "plan": plan}

    def increase_demand(self, zone_id: str = "ZONE_A") -> Dict:
        result = self.process_incident_report(
            f"{zone_id} demand surge. Approximately 1500 additional people affected. Immediate support required.",
            source="simulation",
            zone_id=zone_id,
            auto_replan=True,
        )
        self._publish_scenario("INCREASE DEMAND", extra={"zone_id": zone_id})
        return result

    def run_replan(self) -> Dict:
        plan = self.generate_allocation_plan(trigger="manual_replan")
        self._publish_scenario("RUN REPLAN", extra={"plan_id": plan.get("plan_id")})
        return plan

    def _update_zone_priority(self, zone: Zone, incident: Incident):
        incidents = self.db.query(Incident).filter(Incident.zone_id == zone.id, Incident.status == "active").all()
        total_affected = sum(i.affected_population or 0 for i in incidents)
        total_vulnerable = sum(i.vulnerable_population or 0 for i in incidents)
        needs = self.db.query(Need).filter(Need.zone_id == zone.id).all()
        total_required = sum(n.quantity_required or 0 for n in needs)
        total_fulfilled = sum(n.quantity_fulfilled or 0 for n in needs)
        deficit_ratio = (total_required - total_fulfilled) / max(total_required, 1)
        latest_incident = max(incidents, key=lambda i: i.timestamp) if incidents else incident
        hours_since = max((datetime.utcnow() - latest_incident.timestamp).total_seconds() / 3600, 0.05)
        severities = []
        for i in incidents:
            if i.analysis_result and i.analysis_result.get("severity") is not None:
                severities.append(i.analysis_result.get("severity", 5))
        avg_severity = sum(severities) / max(len(severities), 1) if severities else 5.0
        priority, breakdown = PriorityCalculator.calculate_priority(
            severity=avg_severity,
            affected_population=total_affected,
            vulnerable_population=total_vulnerable,
            total_population=zone.population or 10000,
            resource_deficit_ratio=deficit_ratio,
            hours_since_incident=hours_since,
        )
        zone.priority_score = priority
        zone.severity = avg_severity
        zone.priority_breakdown = breakdown

    def _current_snapshot(self) -> Dict:
        zones = self.db.query(Zone).all()
        resources = self.db.query(Resource).all()
        incidents = self.db.query(Incident).filter(Incident.status == "active").all()
        affected = {}
        for i in incidents:
            affected[i.zone_id] = affected.get(i.zone_id, 0) + (i.affected_population or 0)
        return {
            "zones": [{**self._zone_to_dict(z), "affected_population": affected.get(z.id, 0)} for z in zones],
            "resources": [self._resource_to_dict(r) for r in resources],
        }

    def _allocation_dicts(self, status: Optional[str] = None) -> List[Dict]:
        q = self.db.query(Allocation)
        if status:
            q = q.filter(Allocation.status == status)
        else:
            q = q.filter(Allocation.status.in_(["pending", "approved"]))
        return [
            {"id": a.id, "resource_id": a.resource_id, "zone_id": a.zone_id, "quantity": a.quantity, "status": a.status, "reason": a.reason}
            for a in q.all()
        ]

    def _counts_by_zone(self, allocations: List[Dict]) -> Dict[str, Dict[str, float]]:
        counts: Dict[str, Dict[str, float]] = {}
        resources = {r.id: r for r in self.db.query(Resource).all()}
        for a in allocations:
            res = resources.get(a["resource_id"])
            rtype = res.type if res else "unknown"
            counts.setdefault(a["zone_id"], {})
            counts[a["zone_id"]][rtype] = counts[a["zone_id"]].get(rtype, 0) + (a.get("quantity") or 0)
        return counts

    def _moves(self, old_alloc, new_alloc, resources_map):
        old_by_res = {}
        for a in old_alloc:
            old_by_res[a["resource_id"]] = a["zone_id"]
        moves = []
        for a in new_alloc:
            prev = old_by_res.get(a["resource_id"])
            if prev and prev != a["zone_id"]:
                res = resources_map.get(a["resource_id"], {})
                moves.append({
                    "resource_id": a["resource_id"],
                    "name": res.get("name"),
                    "from_zone": prev,
                    "to_zone": a["zone_id"],
                    "reason": a.get("reason"),
                })
        return moves

    def _get_needs_by_zone(self) -> Dict[str, Dict[str, float]]:
        needs = self.db.query(Need).all()
        result: Dict[str, Dict[str, float]] = {}
        for need in needs:
            result.setdefault(need.zone_id, {})
            result[need.zone_id][need.resource_type] = result[need.zone_id].get(need.resource_type, 0) + (
                need.quantity_remaining or need.quantity_required or 0
            )
        return result

    def _calculate_distances(self, resources, zones, blocked_routes):
        blocked_zones = {b.get("zone_id") for b in (blocked_routes or []) if b.get("blocked")}
        distances = {}
        for resource in resources:
            for zone in zones:
                if resource.get("latitude") and zone.get("latitude"):
                    dist = calculate_distance_km(
                        resource["latitude"], resource["longitude"],
                        zone["latitude"], zone["longitude"],
                    )
                    if zone["id"] in blocked_zones:
                        dist = 9999
                    distances[(resource["id"], zone["id"])] = dist
        return distances

    def _zone_to_dict(self, zone: Zone) -> Dict:
        return {
            "id": zone.id,
            "name": zone.name,
            "latitude": zone.latitude,
            "longitude": zone.longitude,
            "population": zone.population,
            "priority_score": zone.priority_score,
            "priority_breakdown": zone.priority_breakdown,
            "severity": zone.severity,
            "status": zone.status,
        }

    def _resource_to_dict(self, resource: Resource) -> Dict:
        return {
            "id": resource.id,
            "name": resource.name,
            "type": resource.type,
            "agency_id": resource.agency_id,
            "latitude": resource.latitude,
            "longitude": resource.longitude,
            "quantity": resource.quantity,
            "unit": resource.unit,
            "status": resource.status,
            "capabilities": resource.capabilities,
            "current_zone_id": resource.current_zone_id,
            "eta_minutes": resource.eta_minutes,
        }

    def _publish_scenario(self, summary: str, correlation_id: Optional[str] = None, extra: Optional[Dict] = None):
        from app.core.events import build_event, event_bus
        event_bus.publish(build_event(
            "scenario.updated",
            summary,
            correlation_id=correlation_id,
            actor="operator",
            extra=extra,
        ))

    def _emit_pending(self):
        from app.core.events import event_bus
        pending = list(self._pending_events)
        self._pending_events.clear()
        for event in pending:
            event_bus.publish(event)

    def _log_event(
        self,
        event_type: str,
        description: str,
        actor: Optional[str] = None,
        agent: Optional[str] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
        commit: bool = True,
        reason: Optional[str] = None,
    ):
        from app.core.events import events_from_audit

        audit_id = f"evt_{uuid.uuid4().hex[:8]}"
        self.db.add(AuditEvent(
            id=audit_id,
            event_type=event_type,
            description=description,
            actor=actor or "system",
            agent=agent,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason or description,
            correlation_id=correlation_id,
        ))
        self._pending_events.extend(events_from_audit(
            audit_id=audit_id,
            audit_type=event_type,
            description=description,
            actor=actor,
            agent=agent,
            correlation_id=correlation_id,
            new_state=new_state,
            previous_state=previous_state,
        ))
        if not commit:
            return
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            self._pending_events.clear()
            return
        self._emit_pending()
