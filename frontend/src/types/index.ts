export interface Zone {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  population: number;
  vulnerable_population: number;
  severity: number;
  priority_score: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Incident {
  id: string;
  zone_id: string;
  source: string;
  source_reference?: string;
  report_text: string;
  incident_type?: string;
  timestamp: string;
  affected_population?: number;
  vulnerable_population?: number;
  confidence?: number;
  status: string;
  duplicate_group_id?: string;
  created_at: string;
}

export interface Resource {
  id: string;
  name: string;
  type: string;
  agency_id: string;
  latitude?: number;
  longitude?: number;
  quantity?: number;
  unit?: string;
  capacity?: number;
  capabilities?: string[];
  status: string;
  current_zone_id?: string;
  available_at?: string;
  eta_minutes?: number;
  created_at: string;
  updated_at: string;
}

export interface Allocation {
  id: string;
  resource_id: string;
  zone_id: string;
  quantity?: number;
  priority?: number;
  eta_minutes?: number;
  reason?: string;
  status: string;
  plan_id?: string;
  created_at: string;
  approved_at?: string;
}

export interface CoordinationTask {
  id: string;
  agency_id: string;
  allocation_id?: string;
  action: string;
  status: string;
  assigned_at: string;
  approved_at?: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  actor?: string;
  agent?: string;
  event_type: string;
  description: string;
  input_reference?: string;
  previous_state?: any;
  new_state?: any;
  reason?: string;
  correlation_id?: string;
}

export interface AllocationPlan {
  plan_id: string;
  allocations: Allocation[];
  unmet_demands: Array<{
    zone_id: string;
    resource_type: string;
    required: number;
    allocated: number;
    deficit: number;
  }>;
  coordination_tasks: CoordinationTask[];
  explanation: string;
  timestamp: string;
  correlation_id?: string;
}
