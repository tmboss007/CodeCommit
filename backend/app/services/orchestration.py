from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import uuid
from datetime import datetime
from app.models import (
    Zone, Incident, Need, Resource, Allocation, CoordinationTask, AuditEvent,
    AppState, ReplanningEvent, Agency,
)
from app.agents.core import SituationAgent, DuplicateDetectionAgent, CoordinationAgent
from app.agents.replanning import ReplanningAgent
from app.services.priority import PriorityCalculator, NeedsCalculator, calculate_distance_km
from app.services.optimizer import ResourceOptimizer, EXCLUSIVE_TYPES
from app.core.database import Base, engine
from app.services.demo_seed import seed_base_entities, INITIAL_REPORTS, URGENT_ZONE_A_REPORT

ALLOCATABLE = {"available"}


class OrchestrationService:
    def __init__(self, db: Session):
        self.db = db
        self.situation_agent = SituationAgent()
        self.duplicate_agent = DuplicateDetectionAgent()
        self.coordination_agent = CoordinationAgent()
        self.replanning_agent = ReplanningAgent()
        self.optimizer = ResourceOptimizer()

    def _get_state(self) -> AppState:
        state = self.db.query(AppState).filter(AppState.id == "singleton").first()
        if not state:
            state = AppState(id="singleton", blocked_routes=[], last_snapshot={"zones": [], "resources": []}, data_mode="SIMULATION")
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

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

        old_snapshot = self._current_snapshot()

        self._log_event(
            "INCIDENT_CREATED",
            "Situation Agent received a new report",
            agent="Situation Agent",
            correlation_id=correlation_id,
            new_state={"source": source},
        )

        situation_result = self.situation_agent.analyze_report(report_text, zone_id)
        resolved_zone = situation_result.get("zone_id") or zone_id or "ZONE_A"
        situation_result["zone_id"] = resolved_zone

        existing_incidents = self.db.query(Incident).filter(
            Incident.zone_id == resolved_zone,
            Incident.status == "active",
        ).all()

        duplicate_result = self.duplicate_agent.check_duplicate(
            report_text,
            [{"id": i.id, "zone_id": i.zone_id, "incident_type": i.incident_type,
              "timestamp": i.timestamp, "report_text": i.report_text} for i in existing_incidents],
            zone_id=resolved_zone,
            incident_type=situation_result.get("incident_type") or "other",
        )

        self._log_event(
            "DUPLICATE_DETECTED" if duplicate_result.get("is_duplicate") else "INCIDENT_ANALYZED",
            duplicate_result.get("explanation") or "Duplicate Agent evaluated overlap",
            agent="Duplicate Agent",
            correlation_id=correlation_id,
            new_state=duplicate_result,
        )

        affected = situation_result.get("affected_population")
        if affected is None:
            affected = 400
            situation_result["affected_population"] = affected
            situation_result["population_estimated"] = True

        vulnerable = situation_result.get("vulnerable_population")
        if vulnerable is None:
            vulnerable = int(affected * 0.16)
            situation_result["vulnerable_population"] = vulnerable

        incident = Incident(
            id=f"inc_{uuid.uuid4().hex[:8]}",
            zone_id=resolved_zone,
            source=source,
            report_text=report_text,
            incident_type=situation_result.get("incident_type"),
            affected_population=affected,
            vulnerable_population=vulnerable,
            confidence=situation_result.get("confidence"),
            status="active",
            duplicate_group_id=(duplicate_result.get("matched_incidents") or [None])[0],
            duplicate_status=duplicate_result.get("duplicate_status") or "NEW",
            analysis_result=situation_result,
        )
        self.db.add(incident)

        needs_list = NeedsCalculator.calculate_needs(
            affected,
            vulnerable,
            situation_result.get("incident_type", "other"),
            situation_result.get("severity", 5.0),
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

        zone = self.db.query(Zone).filter(Zone.id == resolved_zone).first()
        old_priority = zone.priority_score if zone else None
        if zone:
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

        should_replan, reason, details = self.replanning_agent.should_replan(
            old_snapshot,
            self._current_snapshot(),
            self._allocation_dicts(status="approved"),
        )
        if not should_replan and old_priority is not None and zone and abs(zone.priority_score - old_priority) >= 15:
            should_replan = True
            reason = f"Zone {zone.id} priority change: {old_priority:.0f} → {zone.priority_score:.0f}"
            details = {"priority_changes": [{"zone_id": zone.id, "old_priority": old_priority, "new_priority": zone.priority_score}]}

        result = {
            "incident_id": incident.id,
            "zone_id": incident.zone_id,
            "situation_analysis": situation_result,
            "duplicate_check": duplicate_result,
            "needs_created": len(needs_list),
            "needs": needs_list,
            "zone_priority_updated": zone.priority_score if zone else None,
            "priority_breakdown": zone.priority_breakdown if zone else None,
            "replanning_required": should_replan,
            "replanning_reason": reason,
            "correlation_id": correlation_id,
            "plan": None,
        }

        if auto_replan and should_replan:
            self._log_event(
                "REPLAN_TRIGGERED",
                f"Replanning Evaluator: {reason}",
                agent="Replanning Evaluator",
                correlation_id=correlation_id,
                new_state=details,
            )
            result["plan"] = self.generate_allocation_plan(correlation_id=correlation_id, trigger=reason)

        return result

    def generate_allocation_plan(self, correlation_id: Optional[str] = None, trigger: str = "manual") -> Dict:
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:8]}"

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        app_state = self._get_state()
        old_allocations = self._allocation_dicts()

        pending = self.db.query(Allocation).filter(Allocation.status == "pending").all()
        for alloc in pending:
            alloc.status = "superseded"

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

        allocation_objs = []
        for alloc in allocations:
            resource = self.db.query(Resource).filter(Resource.id == alloc["resource_id"]).first()
            from_zone = resource.current_zone_id if resource else None
            alloc["from_zone_id"] = from_zone
            obj = Allocation(
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
            )
            self.db.add(obj)
            allocation_objs.append(obj)

        self.db.commit()

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
                action=task["action"],
                status="pending",
            )
            self.db.add(obj)
            task_objs.append(obj)

        delta = self.replanning_agent.compute_allocation_delta(old_allocations, allocations)
        delta["before_by_zone"] = self._counts_by_zone(old_allocations)
        delta["after_by_zone"] = self._counts_by_zone(allocations)
        delta["moves"] = self._moves(old_allocations, allocations, resources_map)

        app_state.last_plan_id = plan_id
        app_state.last_snapshot = self._current_snapshot()
        app_state.last_delta = delta
        app_state.last_unmet = unmet_demands
        app_state.last_explanation = explanation
        app_state.updated_at = datetime.utcnow()

        self.db.add(ReplanningEvent(
            id=f"replan_{uuid.uuid4().hex[:8]}",
            trigger=trigger,
            old_plan_id=None,
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

    def reset_world(self):
        seed_base_entities(self.db)
        self._get_state()
        self._log_event("RESOURCE_STATE_CHANGED", "Simulation reset to empty seeded inventory", agent="Simulation Engine")
        self.db.commit()
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
        return {"status": "loaded", "reports": reports, "plan": plan, "correlation_id": correlation_id}

    def inject_urgent_zone_a(self) -> Dict:
        state = self._get_state()
        blocked = list(state.blocked_routes or [])
        blocked.append({"zone_id": "ZONE_A", "reason": "two rescue routes inaccessible", "blocked": False})
        state.blocked_routes = blocked
        self.db.commit()
        return self.process_incident_report(
            URGENT_ZONE_A_REPORT,
            source="simulation",
            zone_id="ZONE_A",
            auto_replan=True,
        )

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
        should, reason, details = self.replanning_agent.should_replan(old, self._current_snapshot(), self._allocation_dicts())
        plan = None
        if should:
            plan = self.generate_allocation_plan(trigger=reason)
        return {"resource_id": resource_id, "status": "unavailable", "replanning_required": should, "plan": plan}

    def block_route(self, zone_id: str = "ZONE_A") -> Dict:
        state = self._get_state()
        blocked = list(state.blocked_routes or [])
        blocked.append({"zone_id": zone_id, "blocked": True, "reason": "route blocked by simulation"})
        state.blocked_routes = blocked
        self._log_event("RESOURCE_STATE_CHANGED", f"Route into {zone_id} blocked", agent="Simulation Engine")
        self.db.commit()
        plan = self.generate_allocation_plan(trigger=f"Route to {zone_id} unavailable")
        return {"blocked": zone_id, "plan": plan}

    def increase_demand(self, zone_id: str = "ZONE_A") -> Dict:
        return self.process_incident_report(
            f"{zone_id} demand surge. Approximately 1500 additional people affected. Immediate support required.",
            source="simulation",
            zone_id=zone_id,
            auto_replan=True,
        )

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

    def _log_event(
        self,
        event_type: str,
        description: str,
        actor: Optional[str] = None,
        agent: Optional[str] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        correlation_id: Optional[str] = None,
    ):
        self.db.add(AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            description=description,
            actor=actor or "system",
            agent=agent,
            previous_state=previous_state,
            new_state=new_state,
            reason=description,
            correlation_id=correlation_id,
        ))
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
