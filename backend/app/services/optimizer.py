from typing import List, Dict, Tuple, Optional
from ortools.linear_solver import pywraplp
import uuid

class ResourceOptimizer:
    """Optimize resource allocation using constraint-based optimization."""

    def __init__(self):
        self.solver = None

    def optimize_allocation(
        self,
        zones: List[Dict],
        resources: List[Dict],
        needs: Dict[str, Dict[str, float]],  # zone_id -> {resource_type -> quantity}
        distances: Dict[Tuple[str, str], float]  # (resource_id, zone_id) -> distance_km
    ) -> Tuple[List[Dict], List[Dict], str]:
        """
        Optimize resource allocation to zones.

        Returns: (allocations, unmet_demands, explanation)
        """
        self.solver = pywraplp.Solver.CreateSolver('SCIP')
        if not self.solver:
            return self._fallback_greedy_allocation(zones, resources, needs, distances)

        # Decision variables: allocation[resource_id][zone_id] = quantity
        allocation_vars = {}

        for resource in resources:
            if resource['status'] != 'available':
                continue

            allocation_vars[resource['id']] = {}
            for zone in zones:
                var_name = f"alloc_{resource['id']}_{zone['id']}"
                max_qty = resource.get('quantity', 1) or 1
                allocation_vars[resource['id']][zone['id']] = \
                    self.solver.NumVar(0, max_qty, var_name)

        # Constraint: Each resource can only allocate up to its capacity
        for resource in resources:
            if resource['id'] not in allocation_vars:
                continue

            constraint = self.solver.Constraint(
                0,
                resource.get('quantity', 1) or 1
            )
            for zone_id in allocation_vars[resource['id']]:
                constraint.SetCoefficient(
                    allocation_vars[resource['id']][zone_id],
                    1
                )

        # Objective: Maximize priority-weighted coverage, minimize distance
        objective = self.solver.Objective()

        for resource in resources:
            if resource['id'] not in allocation_vars:
                continue

            for zone in zones:
                zone_id = zone['id']
                if zone_id not in allocation_vars[resource['id']]:
                    continue

                # Priority weight (0-100)
                priority = zone.get('priority_score', 50)

                # Distance penalty
                dist = distances.get((resource['id'], zone_id), 100)
                distance_penalty = 1.0 / (1.0 + dist / 50.0)  # Normalize

                # Resource-need matching bonus
                resource_type = resource['type']
                zone_needs = needs.get(zone_id, {})
                need_match = 1.0
                if resource_type in zone_needs and zone_needs[resource_type] > 0:
                    need_match = 2.0  # Double weight if type matches need

                # Combined coefficient
                coefficient = priority * distance_penalty * need_match

                objective.SetCoefficient(
                    allocation_vars[resource['id']][zone_id],
                    coefficient
                )

        objective.SetMaximization()

        # Solve
        status = self.solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            return self._extract_solution(
                allocation_vars, resources, zones, needs, distances
            )
        else:
            return self._fallback_greedy_allocation(zones, resources, needs, distances)

    def _extract_solution(
        self,
        allocation_vars,
        resources,
        zones,
        needs,
        distances
    ) -> Tuple[List[Dict], List[Dict], str]:
        """Extract allocation results from solver."""
        allocations = []

        for resource in resources:
            if resource['id'] not in allocation_vars:
                continue

            for zone in zones:
                zone_id = zone['id']
                if zone_id not in allocation_vars[resource['id']]:
                    continue

                qty = allocation_vars[resource['id']][zone_id].solution_value()

                if qty > 0.01:  # Threshold for meaningful allocation
                    dist = distances.get((resource['id'], zone_id), 0)
                    eta = int((dist / 60) * 60) + 10  # Rough ETA

                    allocations.append({
                        'id': f"alloc_{uuid.uuid4().hex[:8]}",
                        'resource_id': resource['id'],
                        'zone_id': zone_id,
                        'quantity': round(qty, 2),
                        'priority': zone.get('priority_score', 50),
                        'eta_minutes': eta,
                        'reason': f"Optimized allocation: {resource['name']} to {zone['name']} (Priority: {zone.get('priority_score', 50):.0f}, Distance: {dist:.1f}km)",
                        'status': 'pending'
                    })

        # Calculate unmet demands
        unmet = self._calculate_unmet_demands(allocations, needs, resources)

        explanation = f"Optimal allocation computed. {len(allocations)} assignments. Objective value: {self.solver.Objective().Value():.2f}"

        return allocations, unmet, explanation

    def _fallback_greedy_allocation(
        self,
        zones,
        resources,
        needs,
        distances
    ) -> Tuple[List[Dict], List[Dict], str]:
        """Greedy allocation fallback when solver unavailable."""
        allocations = []

        # Sort zones by priority (descending)
        sorted_zones = sorted(
            zones,
            key=lambda z: z.get('priority_score', 0),
            reverse=True
        )

        available_resources = {r['id']: r.get('quantity', 1) for r in resources if r['status'] == 'available'}

        for zone in sorted_zones:
            zone_needs = needs.get(zone['id'], {})

            for resource in resources:
                if resource['id'] not in available_resources:
                    continue
                if available_resources[resource['id']] <= 0:
                    continue

                # Match resource type to needs
                resource_type = resource['type']
                if resource_type in zone_needs and zone_needs[resource_type] > 0:
                    qty = min(
                        available_resources[resource['id']],
                        zone_needs[resource_type]
                    )

                    if qty > 0:
                        dist = distances.get((resource['id'], zone['id']), 0)
                        eta = int((dist / 60) * 60) + 10

                        allocations.append({
                            'id': f"alloc_{uuid.uuid4().hex[:8]}",
                            'resource_id': resource['id'],
                            'zone_id': zone['id'],
                            'quantity': round(qty, 2),
                            'priority': zone.get('priority_score', 50),
                            'eta_minutes': eta,
                            'reason': f"Greedy allocation: {resource['name']} to {zone['name']} (Priority: {zone.get('priority_score', 50):.0f})",
                            'status': 'pending'
                        })

                        available_resources[resource['id']] -= qty

        unmet = self._calculate_unmet_demands(allocations, needs, resources)

        return allocations, unmet, f"Greedy allocation completed. {len(allocations)} assignments."

    def _calculate_unmet_demands(
        self,
        allocations: List[Dict],
        needs: Dict[str, Dict[str, float]],
        resources: List[Dict]
    ) -> List[Dict]:
        """Calculate remaining unmet demands after allocation."""
        fulfilled = {}

        for alloc in allocations:
            zone_id = alloc['zone_id']
            resource = next((r for r in resources if r['id'] == alloc['resource_id']), None)
            if not resource:
                continue

            resource_type = resource['type']

            if zone_id not in fulfilled:
                fulfilled[zone_id] = {}
            if resource_type not in fulfilled[zone_id]:
                fulfilled[zone_id][resource_type] = 0

            fulfilled[zone_id][resource_type] += alloc['quantity']

        unmet = []
        for zone_id, zone_needs in needs.items():
            for resource_type, required in zone_needs.items():
                allocated = fulfilled.get(zone_id, {}).get(resource_type, 0)
                deficit = max(0, required - allocated)

                if deficit > 0:
                    unmet.append({
                        'zone_id': zone_id,
                        'resource_type': resource_type,
                        'required': required,
                        'allocated': allocated,
                        'deficit': deficit
                    })

        return unmet
