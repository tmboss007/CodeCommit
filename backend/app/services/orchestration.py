from sqlalchemy.orm import Session
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timedelta
from app.models import Zone, Incident, Need, Resource, Allocation, CoordinationTask, AuditEvent
from app.agents.core import SituationAgent, DuplicateDetectionAgent, CoordinationAgent
from app.agents.replanning import ReplanningAgent
from app.services.priority import PriorityCalculator, NeedsCalculator, calculate_distance_km
from app.services.optimizer import ResourceOptimizer

class OrchestrationService:
    """Main service orchestrating the disaster response workflow."""

    def __init__(self, db: Session):
        self.db = db
        self.situation_agent = SituationAgent()
        self.duplicate_agent = DuplicateDetectionAgent()
        self.coordination_agent = CoordinationAgent()
        self.replanning_agent = ReplanningAgent()
        self.optimizer = ResourceOptimizer()

    def process_incident_report(
        self,
        report_text: str,
        source: str,
        zone_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict:
        """
        Process new incident report through full pipeline.

        Returns complete workflow result with allocations.
        """
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:8]}"

        # Step 1: Situation Agent - Extract structured information
        self._log_event(
            "situation_agent_start",
            "Situation Agent analyzing report",
            correlation_id=correlation_id
        )

        situation_result = self.situation_agent.analyze_report(report_text, zone_id)

        # Step 2: Check for duplicates
        self._log_event(
            "duplicate_check_start",
            "Checking for duplicate incidents",
            correlation_id=correlation_id
        )

        existing_incidents = self.db.query(Incident).filter(
            Incident.zone_id == situation_result['zone_id'],
            Incident.status == 'active'
        ).all()

        duplicate_result = self.duplicate_agent.check_duplicate(
            report_text,
            [{'id': i.id, 'zone_id': i.zone_id, 'incident_type': i.incident_type,
              'timestamp': i.timestamp, 'report_text': i.report_text}
             for i in existing_incidents]
        )

        # Step 3: Create incident
        incident = Incident(
            id=f"inc_{uuid.uuid4().hex[:8]}",
            zone_id=situation_result['zone_id'],
            source=source,
            report_text=report_text,
            incident_type=situation_result.get('incident_type'),
            affected_population=situation_result.get('affected_population'),
            vulnerable_population=situation_result.get('vulnerable_population'),
            confidence=situation_result.get('confidence'),
            status='active',
            duplicate_group_id=duplicate_result['matched_incidents'][0] if duplicate_result['is_duplicate'] else None,
            analysis_result=situation_result
        )
        self.db.add(incident)

        # Step 4: Needs Assessment Agent
        self._log_event(
            "needs_assessment_start",
            "Needs Assessment Agent calculating requirements",
            correlation_id=correlation_id
        )

        needs_list = NeedsCalculator.calculate_needs(
            situation_result.get('affected_population', 0),
            situation_result.get('vulnerable_population', 0),
            situation_result.get('incident_type', 'other'),
            situation_result.get('severity', 5.0)
        )

        for need in needs_list:
            need_obj = Need(
                id=f"need_{uuid.uuid4().hex[:8]}",
                incident_id=incident.id,
                zone_id=incident.zone_id,
                resource_type=need['type'],
                quantity_required=need['quantity'],
                quantity_remaining=need['quantity'],
                urgency=need['urgency'],
                unit=need.get('unit')
            )
            self.db.add(need_obj)

        # Step 5: Update zone state
        zone = self.db.query(Zone).filter(Zone.id == situation_result['zone_id']).first()
        if zone:
            # Recalculate priority
            self._update_zone_priority(zone, incident)

        self.db.commit()

        self._log_event(
            "incident_processed",
            f"Incident {incident.id} processed successfully",
            new_state={'incident_id': incident.id, 'zone_id': zone.id if zone else None},
            correlation_id=correlation_id
        )

        # Step 6: Check if replanning needed
        should_replan, reason, details = self._check_replanning_trigger()

        result = {
            'incident_id': incident.id,
            'zone_id': incident.zone_id,
            'situation_analysis': situation_result,
            'duplicate_check': duplicate_result,
            'needs_created': len(needs_list),
            'zone_priority_updated': zone.priority_score if zone else None,
            'replanning_required': should_replan,
            'replanning_reason': reason,
            'correlation_id': correlation_id
        }

        return result

    def generate_allocation_plan(self, correlation_id: Optional[str] = None) -> Dict:
        """Generate optimal resource allocation plan."""
        if not correlation_id:
            correlation_id = f"corr_{uuid.uuid4().hex[:8]}"

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        self._log_event(
            "optimization_start",
            "Starting resource optimization",
            correlation_id=correlation_id
        )

        # Get active zones
        zones = self.db.query(Zone).filter(Zone.status == 'active').all()
        zones_data = [self._zone_to_dict(z) for z in zones]

        # Get available resources
        resources = self.db.query(Resource).filter(Resource.status == 'available').all()
        resources_data = [self._resource_to_dict(r) for r in resources]

        # Get unmet needs by zone
        needs_by_zone = self._get_needs_by_zone()

        # Calculate distances
        distances = self._calculate_distances(resources_data, zones_data)

        # Run optimization
        allocations, unmet_demands, explanation = self.optimizer.optimize_allocation(
            zones_data,
            resources_data,
            needs_by_zone,
            distances
        )

        # Save allocations
        allocation_objs = []
        for alloc in allocations:
            alloc_obj = Allocation(
                id=alloc['id'],
                resource_id=alloc['resource_id'],
                zone_id=alloc['zone_id'],
                quantity=alloc.get('quantity'),
                priority=alloc.get('priority'),
                eta_minutes=alloc.get('eta_minutes'),
                reason=alloc.get('reason'),
                status='pending',
                plan_id=plan_id
            )
            self.db.add(alloc_obj)
            allocation_objs.append(alloc_obj)

        self.db.commit()

        # Generate coordination tasks
        self._log_event(
            "coordination_start",
            "Generating coordination tasks",
            correlation_id=correlation_id
        )

        resources_map = {r['id']: r for r in resources_data}
        zones_map = {z['id']: z for z in zones_data}
        agencies = self.db.query(Resource.agency_id).distinct().all()
        agencies_map = {a[0]: {'id': a[0]} for a in agencies}

        tasks = self.coordination_agent.generate_tasks(
            allocations,
            resources_map,
            zones_map,
            agencies_map
        )

        task_objs = []
        for task in tasks:
            task_obj = CoordinationTask(
                id=f"task_{uuid.uuid4().hex[:8]}",
                agency_id=task['agency_id'],
                allocation_id=task.get('allocation_id'),
                action=task['action'],
                status='pending'
            )
            self.db.add(task_obj)
            task_objs.append(task_obj)

        self.db.commit()

        self._log_event(
            "plan_generated",
            f"Allocation plan {plan_id} generated with {len(allocations)} allocations",
            new_state={'plan_id': plan_id, 'allocation_count': len(allocations)},
            correlation_id=correlation_id
        )

        return {
            'plan_id': plan_id,
            'allocations': allocations,
            'unmet_demands': unmet_demands,
            'coordination_tasks': [{'id': t.id, 'agency_id': t.agency_id, 'action': t.action} for t in task_objs],
            'explanation': explanation,
            'timestamp': datetime.utcnow(),
            'correlation_id': correlation_id
        }

    def _update_zone_priority(self, zone: Zone, incident: Incident):
        """Recalculate and update zone priority score."""
        # Get all active incidents in zone
        incidents = self.db.query(Incident).filter(
            Incident.zone_id == zone.id,
            Incident.status == 'active'
        ).all()

        # Aggregate affected population
        total_affected = sum(i.affected_population or 0 for i in incidents)
        total_vulnerable = sum(i.vulnerable_population or 0 for i in incidents)

        # Get resource deficit
        needs = self.db.query(Need).filter(Need.zone_id == zone.id).all()
        total_required = sum(n.quantity_required for n in needs)
        total_fulfilled = sum(n.quantity_fulfilled for n in needs)
        deficit_ratio = (total_required - total_fulfilled) / max(total_required, 1)

        # Calculate time criticality (hours since most recent incident)
        latest_incident = max(incidents, key=lambda i: i.timestamp) if incidents else incident
        hours_since = (datetime.utcnow() - latest_incident.timestamp).total_seconds() / 3600

        # Average severity
        avg_severity = sum(i.analysis_result.get('severity', 5) for i in incidents if i.analysis_result) / max(len(incidents), 1)

        # Calculate priority
        priority, breakdown = PriorityCalculator.calculate_priority(
            severity=avg_severity,
            affected_population=total_affected,
            vulnerable_population=total_vulnerable,
            total_population=zone.population or 10000,
            resource_deficit_ratio=deficit_ratio,
            hours_since_incident=hours_since
        )

        zone.priority_score = priority
        zone.severity = avg_severity

    def _check_replanning_trigger(self) -> tuple:
        """Check if system state requires replanning."""
        # Get current state
        zones = self.db.query(Zone).all()
        resources = self.db.query(Resource).all()

        new_state = {
            'zones': [self._zone_to_dict(z) for z in zones],
            'resources': [self._resource_to_dict(r) for r in resources]
        }

        # Get last plan state (simplified - would store this)
        old_state = {'zones': [], 'resources': []}  # Would retrieve from cache/db

        current_allocations = self.db.query(Allocation).filter(Allocation.status == 'approved').all()

        should_replan, reason, details = self.replanning_agent.should_replan(
            old_state,
            new_state,
            [{'id': a.id, 'resource_id': a.resource_id, 'zone_id': a.zone_id} for a in current_allocations]
        )

        return should_replan, reason, details

    def _get_needs_by_zone(self) -> Dict[str, Dict[str, float]]:
        """Get aggregated unmet needs by zone."""
        needs = self.db.query(Need).all()
        result = {}

        for need in needs:
            if need.zone_id not in result:
                result[need.zone_id] = {}
            if need.resource_type not in result[need.zone_id]:
                result[need.zone_id][need.resource_type] = 0
            result[need.zone_id][need.resource_type] += need.quantity_remaining or need.quantity_required

        return result

    def _calculate_distances(self, resources: List[Dict], zones: List[Dict]) -> Dict:
        """Calculate distances between all resources and zones."""
        distances = {}
        for resource in resources:
            for zone in zones:
                if resource.get('latitude') and zone.get('latitude'):
                    dist = calculate_distance_km(
                        resource['latitude'], resource['longitude'],
                        zone['latitude'], zone['longitude']
                    )
                    distances[(resource['id'], zone['id'])] = dist
        return distances

    def _zone_to_dict(self, zone: Zone) -> Dict:
        return {
            'id': zone.id,
            'name': zone.name,
            'latitude': zone.latitude,
            'longitude': zone.longitude,
            'population': zone.population,
            'priority_score': zone.priority_score,
            'severity': zone.severity,
            'status': zone.status
        }

    def _resource_to_dict(self, resource: Resource) -> Dict:
        return {
            'id': resource.id,
            'name': resource.name,
            'type': resource.type,
            'agency_id': resource.agency_id,
            'latitude': resource.latitude,
            'longitude': resource.longitude,
            'quantity': resource.quantity,
            'unit': resource.unit,
            'status': resource.status,
            'capabilities': resource.capabilities
        }

    def _log_event(
        self,
        event_type: str,
        description: str,
        actor: Optional[str] = None,
        agent: Optional[str] = None,
        previous_state: Optional[Dict] = None,
        new_state: Optional[Dict] = None,
        correlation_id: Optional[str] = None
    ):
        """Log audit event."""
        event = AuditEvent(
            id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            description=description,
            actor=actor or "system",
            agent=agent,
            previous_state=previous_state,
            new_state=new_state,
            correlation_id=correlation_id
        )
        self.db.add(event)
        try:
            self.db.commit()
        except:
            self.db.rollback()
