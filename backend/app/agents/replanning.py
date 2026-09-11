from typing import Dict, List, Tuple
from datetime import datetime

class ReplanningAgent:
    """Determine when re-planning is required and trigger re-optimization."""

    # Thresholds for triggering replan
    PRIORITY_CHANGE_THRESHOLD = 15  # Priority change by more than 15 points
    SEVERITY_CHANGE_THRESHOLD = 2.0  # Severity change by more than 2 levels
    POPULATION_CHANGE_THRESHOLD = 0.3  # 30% population increase
    RESOURCE_DEFICIT_THRESHOLD = 0.4  # 40% unmet critical needs

    def should_replan(
        self,
        old_state: Dict,
        new_state: Dict,
        current_allocations: List[Dict]
    ) -> Tuple[bool, str, Dict]:
        """
        Determine if re-planning is needed.

        Returns: (should_replan, reason, details)
        """
        triggers = []
        details = {}

        # Check zone priority changes
        old_zones = {z['id']: z for z in old_state.get('zones', [])}
        new_zones = {z['id']: z for z in new_state.get('zones', [])}

        priority_changes = []
        for zone_id, new_zone in new_zones.items():
            old_zone = old_zones.get(zone_id)
            if old_zone:
                old_priority = old_zone.get('priority_score', 0)
                new_priority = new_zone.get('priority_score', 0)
                delta = abs(new_priority - old_priority)

                if delta >= self.PRIORITY_CHANGE_THRESHOLD:
                    priority_changes.append({
                        'zone_id': zone_id,
                        'old_priority': old_priority,
                        'new_priority': new_priority,
                        'delta': delta
                    })
                    triggers.append(f"Zone {zone_id} priority change: {old_priority:.0f} → {new_priority:.0f}")

        if priority_changes:
            details['priority_changes'] = priority_changes

        # Check severity changes
        severity_changes = []
        for zone_id, new_zone in new_zones.items():
            old_zone = old_zones.get(zone_id)
            if old_zone:
                old_severity = old_zone.get('severity', 0)
                new_severity = new_zone.get('severity', 0)
                delta = abs(new_severity - old_severity)

                if delta >= self.SEVERITY_CHANGE_THRESHOLD:
                    severity_changes.append({
                        'zone_id': zone_id,
                        'old_severity': old_severity,
                        'new_severity': new_severity
                    })
                    triggers.append(f"Zone {zone_id} severity escalation: {old_severity:.1f} → {new_severity:.1f}")

        if severity_changes:
            details['severity_changes'] = severity_changes

        # Check population changes
        population_changes = []
        for zone_id, new_zone in new_zones.items():
            old_zone = old_zones.get(zone_id)
            if old_zone:
                old_pop = old_zone.get('affected_population', 0) or 1
                new_pop = new_zone.get('affected_population', 0) or 1
                ratio = (new_pop - old_pop) / old_pop

                if ratio >= self.POPULATION_CHANGE_THRESHOLD:
                    population_changes.append({
                        'zone_id': zone_id,
                        'old_population': old_pop,
                        'new_population': new_pop,
                        'increase_ratio': ratio
                    })
                    triggers.append(f"Zone {zone_id} population increase: {old_pop} → {new_pop} ({ratio*100:.0f}%)")

        if population_changes:
            details['population_changes'] = population_changes

        # Check resource availability changes
        old_resources = {r['id']: r for r in old_state.get('resources', [])}
        new_resources = {r['id']: r for r in new_state.get('resources', [])}

        resource_changes = []
        for res_id, old_res in old_resources.items():
            new_res = new_resources.get(res_id)
            if not new_res:
                resource_changes.append({
                    'resource_id': res_id,
                    'change': 'removed'
                })
                triggers.append(f"Resource {res_id} no longer available")
            elif old_res.get('status') == 'available' and new_res.get('status') != 'available':
                resource_changes.append({
                    'resource_id': res_id,
                    'old_status': old_res.get('status'),
                    'new_status': new_res.get('status')
                })
                triggers.append(f"Resource {res_id} status changed to {new_res.get('status')}")

        if resource_changes:
            details['resource_changes'] = resource_changes

        # Check unmet critical needs
        unmet_ratio = new_state.get('unmet_critical_ratio', 0)
        if unmet_ratio >= self.RESOURCE_DEFICIT_THRESHOLD:
            triggers.append(f"Critical resource deficit: {unmet_ratio*100:.0f}% unmet")
            details['unmet_critical_ratio'] = unmet_ratio

        # Decision
        should_replan = len(triggers) > 0
        reason = "; ".join(triggers) if triggers else "No material changes detected"

        return should_replan, reason, details

    def compute_allocation_delta(
        self,
        old_allocations: List[Dict],
        new_allocations: List[Dict]
    ) -> Dict:
        """Compute differences between old and new allocation plans."""
        old_map = {(a['resource_id'], a['zone_id']): a for a in old_allocations}
        new_map = {(a['resource_id'], a['zone_id']): a for a in new_allocations}

        added = []
        removed = []
        modified = []

        # Find new allocations
        for key, new_alloc in new_map.items():
            if key not in old_map:
                added.append(new_alloc)
            else:
                old_alloc = old_map[key]
                if old_alloc.get('quantity') != new_alloc.get('quantity'):
                    modified.append({
                        'resource_id': new_alloc['resource_id'],
                        'zone_id': new_alloc['zone_id'],
                        'old_quantity': old_alloc.get('quantity'),
                        'new_quantity': new_alloc.get('quantity')
                    })

        # Find removed allocations
        for key, old_alloc in old_map.items():
            if key not in new_map:
                removed.append(old_alloc)

        return {
            'added': added,
            'removed': removed,
            'modified': modified,
            'summary': f"{len(added)} added, {len(removed)} removed, {len(modified)} modified"
        }
