export function cnJoin(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(' ');
}

export function formatScore(value?: number | null, digits = 0) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(digits);
}

export function severityTier(score?: number | null) {
  const n = Number(score || 0);
  if (n >= 80) return { label: 'CRITICAL' as const, tone: 'critical' as const };
  if (n >= 60) return { label: 'HIGH' as const, tone: 'high' as const };
  if (n >= 40) return { label: 'ELEVATED' as const, tone: 'elevated' as const };
  return { label: 'STABLE' as const, tone: 'stable' as const };
}

export function zoneLetter(zoneId?: string | null) {
  if (!zoneId) return '—';
  const match = String(zoneId).match(/ZONE[_-]?([A-Z0-9]+)/i);
  return match ? match[1].toUpperCase() : String(zoneId);
}

export function resourceCallsign(resource: { id?: string; agency_id?: string; name?: string }) {
  if (resource.agency_id && resource.id) return `${resource.agency_id}-${resource.id}`;
  return resource.id || resource.name || '—';
}

export function kindForActor(agent?: string) {
  const name = (agent || '').toLowerCase();
  if (name.includes('service') || name.includes('engine') || name.includes('evaluator') || name.includes('optimization') || name.includes('needs') || name.includes('priority')) {
    return 'Decision Service';
  }
  if (name.includes('approval') || name.includes('operator')) return 'Operator';
  if (name.includes('agent')) return 'Agent';
  return 'System';
}

export function apiError(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail?.error === 'validation_failed') {
    const bits = (detail.details || []).join(' ');
    return bits ? `Plan was not applied. ${bits}` : 'Plan was not applied. Validation failed.';
  }
  if (detail?.error === 'already_approved') return 'This plan is already approved.';
  if (detail?.error === 'already_rejected') return 'This plan is already rejected.';
  if (detail?.error) return `Plan was not applied. ${detail.error}`;
  return fallback;
}

export const PIPELINE = [
  { match: 'Situation', label: 'Situation Agent', kind: 'Agent' as const },
  { match: 'Duplicate', label: 'Duplicate Agent', kind: 'Agent' as const },
  { match: 'Coordination', label: 'Coordination Agent', kind: 'Agent' as const },
  { match: 'Replanning', label: 'Replanning Agent', kind: 'Agent' as const },
  { match: 'Needs', label: 'Needs Assessment', kind: 'Decision Service' as const },
  { match: 'Priority', label: 'Priority Scoring', kind: 'Decision Service' as const },
  { match: 'Optimization', label: 'Optimization Engine', kind: 'Decision Service' as const },
];

export function pipelineStatus(events: any[], match: string): 'RUNNING' | 'COMPLETED' | 'WAITING' | 'FAILED' | 'TRIGGERED' {
  const related = events.filter((e) => {
    const blob = `${e.agent || ''} ${e.event_type || ''} ${e.description || ''}`;
    return blob.toLowerCase().includes(match.toLowerCase());
  });
  if (!related.length) return 'WAITING';
  const latest = related[0];
  const text = `${latest.event_type || ''} ${latest.description || ''}`.toLowerCase();
  if (text.includes('fail') || text.includes('error')) return 'FAILED';
  if (latest.event_type === 'REPLAN_TRIGGERED') return 'TRIGGERED';
  const age = Date.now() - new Date(latest.timestamp).getTime();
  if (Number.isFinite(age) && age >= 0 && age < 12000) return 'RUNNING';
  return 'COMPLETED';
}

export function affectedInZone(incidents: Array<{ zone_id?: string; affected_population?: number }>, zoneId: string) {
  return incidents
    .filter((i) => i.zone_id === zoneId)
    .reduce((sum, i) => sum + (Number(i.affected_population) || 0), 0);
}

export function deficitLabel(value?: number | null) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const n = Number(value);
  if (n >= 70) return 'High';
  if (n >= 40) return 'Moderate';
  return 'Low';
}

export function formatCount(value?: number | null) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString();
}

export function eventAge(timestamp?: string) {
  if (!timestamp) return '—';
  const ms = Date.now() - new Date(timestamp).getTime();
  if (!Number.isFinite(ms) || ms < 0) return '—';
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h`;
}

export function formatEventLabel(eventType?: string) {
  return (eventType || 'EVENT').replace(/_/g, ' ');
}

export function eventKind(eventType?: string) {
  const t = (eventType || '').toUpperCase();
  if (t.includes('PLAN_APPROVED') || t === 'APPROVAL_GRANTED') return 'approved';
  if (t.includes('REPLAN') || t.includes('ALLOCATION_CHANGED')) return 'replan';
  if (t.includes('RESOURCE')) return 'resource';
  if (t.includes('PRIORITY')) return 'priority';
  return 'default';
}
