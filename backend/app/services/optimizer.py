from typing import List, Dict, Tuple
from ortools.linear_solver import pywraplp
import uuid

EXCLUSIVE_TYPES = {"rescue_team", "medical_team", "fire_team"}
ALLOCATABLE_STATUSES = {"available"}


class ResourceOptimizer:
    """Constraint-based allocation using OR-Tools SCIP, with greedy fallback."""

    def __init__(self):
        self.solver = None

    def optimize_allocation(
        self,
        zones: List[Dict],
        resources: List[Dict],
        needs: Dict[str, Dict[str, float]],
        distances: Dict[Tuple[str, str], float]
    ) -> Tuple[List[Dict], List[Dict], str]:
        self.solver = pywraplp.Solver.CreateSolver("SCIP")
        if not self.solver:
            return self._fallback_greedy_allocation(zones, resources, needs, distances)

        usable = [r for r in resources if r.get("status") in ALLOCATABLE_STATUSES]
        allocation_vars = {}

        for resource in usable:
            allocation_vars[resource["id"]] = {}
            exclusive = resource.get("type") in EXCLUSIVE_TYPES
            max_qty = 1 if exclusive else (resource.get("quantity", 1) or 1)
            for zone in zones:
                var_name = f"alloc_{resource['id']}_{zone['id']}"
                if exclusive:
                    allocation_vars[resource["id"]][zone["id"]] = self.solver.IntVar(0, 1, var_name)
                else:
                    allocation_vars[resource["id"]][zone["id"]] = self.solver.NumVar(0, max_qty, var_name)

        for resource in usable:
            exclusive = resource.get("type") in EXCLUSIVE_TYPES
            cap = 1 if exclusive else (resource.get("quantity", 1) or 1)
            constraint = self.solver.Constraint(0, cap)
            for zone_id in allocation_vars[resource["id"]]:
                constraint.SetCoefficient(allocation_vars[resource["id"]][zone_id], 1)

        resource_types = {r["type"] for r in usable}
        for zone in zones:
            zone_needs = needs.get(zone["id"], {})
            for rtype in resource_types:
                need_qty = float(zone_needs.get(rtype, 0) or 0)
                constraint = self.solver.Constraint(0, need_qty)
                for resource in usable:
                    if resource["type"] != rtype:
                        continue
                    constraint.SetCoefficient(allocation_vars[resource["id"]][zone["id"]], 1)

        objective = self.solver.Objective()
        for resource in usable:
            for zone in zones:
                zone_id = zone["id"]
                zone_needs = needs.get(zone_id, {})
                if resource["type"] not in zone_needs or zone_needs[resource["type"]] <= 0:
                    continue
                dist = distances.get((resource["id"], zone_id), 100)
                if dist >= 9000:
                    continue
                priority = zone.get("priority_score", 50)
                distance_penalty = 1.0 / (1.0 + dist / 50.0)
                coefficient = priority * distance_penalty * 2.0
                objective.SetCoefficient(allocation_vars[resource["id"]][zone_id], coefficient)

        objective.SetMaximization()
        status = self.solver.Solve()

        if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            return self._extract_solution(allocation_vars, resources, zones, needs, distances)
        return self._fallback_greedy_allocation(zones, resources, needs, distances)

    def _extract_solution(self, allocation_vars, resources, zones, needs, distances):
        allocations = []
        for resource in resources:
            if resource["id"] not in allocation_vars:
                continue
            exclusive = resource.get("type") in EXCLUSIVE_TYPES
            for zone in zones:
                zone_id = zone["id"]
                if zone_id not in allocation_vars[resource["id"]]:
                    continue
                qty = allocation_vars[resource["id"]][zone_id].solution_value()
                threshold = 0.5 if exclusive else 0.01
                if qty > threshold:
                    dist = distances.get((resource["id"], zone_id), 0)
                    eta = int(dist / 50.0 * 60) + 10
                    allocations.append({
                        "id": f"alloc_{uuid.uuid4().hex[:8]}",
                        "resource_id": resource["id"],
                        "zone_id": zone_id,
                        "quantity": 1 if exclusive else round(qty, 2),
                        "priority": zone.get("priority_score", 50),
                        "eta_minutes": eta,
                        "reason": (
                            f"{resource['name']} → {zone['name']} because priority is "
                            f"{zone.get('priority_score', 50):.0f}/100, type {resource['type']} matches unmet demand, "
                            f"and simulated ETA is {eta} minutes ({dist:.1f} km)."
                        ),
                        "status": "pending",
                    })
        unmet = self._calculate_unmet_demands(allocations, needs, resources)
        explanation = (
            f"OR-Tools SCIP allocation. {len(allocations)} assignments. "
            f"Objective value: {self.solver.Objective().Value():.2f}"
        )
        return allocations, unmet, explanation

    def _fallback_greedy_allocation(self, zones, resources, needs, distances):
        allocations = []
        sorted_zones = sorted(zones, key=lambda z: z.get("priority_score", 0), reverse=True)
        available_resources = {
            r["id"]: r.get("quantity", 1)
            for r in resources
            if r.get("status") in ALLOCATABLE_STATUSES
        }
        for zone in sorted_zones:
            zone_needs = dict(needs.get(zone["id"], {}))
            for resource in resources:
                if resource["id"] not in available_resources or available_resources[resource["id"]] <= 0:
                    continue
                rtype = resource["type"]
                if rtype not in zone_needs or zone_needs[rtype] <= 0:
                    continue
                dist = distances.get((resource["id"], zone["id"]), 0)
                if dist >= 9000:
                    continue
                qty = min(available_resources[resource["id"]], zone_needs[rtype])
                if resource["type"] in EXCLUSIVE_TYPES:
                    qty = min(qty, 1)
                if qty > 0:
                    eta = int(dist / 50.0 * 60) + 10
                    allocations.append({
                        "id": f"alloc_{uuid.uuid4().hex[:8]}",
                        "resource_id": resource["id"],
                        "zone_id": zone["id"],
                        "quantity": round(qty, 2),
                        "priority": zone.get("priority_score", 50),
                        "eta_minutes": eta,
                        "reason": f"Greedy allocation: {resource['name']} to {zone['name']} (Priority: {zone.get('priority_score', 50):.0f})",
                        "status": "pending",
                    })
                    available_resources[resource["id"]] -= qty
                    zone_needs[rtype] -= qty
        unmet = self._calculate_unmet_demands(allocations, needs, resources)
        return allocations, unmet, f"Greedy allocation completed. {len(allocations)} assignments."

    def _calculate_unmet_demands(self, allocations, needs, resources):
        fulfilled = {}
        for alloc in allocations:
            resource = next((r for r in resources if r["id"] == alloc["resource_id"]), None)
            if not resource:
                continue
            zone_id = alloc["zone_id"]
            fulfilled.setdefault(zone_id, {})
            fulfilled[zone_id][resource["type"]] = fulfilled[zone_id].get(resource["type"], 0) + alloc["quantity"]
        unmet = []
        for zone_id, zone_needs in needs.items():
            for resource_type, required in zone_needs.items():
                allocated = fulfilled.get(zone_id, {}).get(resource_type, 0)
                deficit = max(0, required - allocated)
                if deficit > 0:
                    unmet.append({
                        "zone_id": zone_id,
                        "resource_type": resource_type,
                        "required": required,
                        "allocated": allocated,
                        "deficit": deficit,
                    })
        return unmet
