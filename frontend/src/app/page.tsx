'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useState } from 'react';
import { snapshotAPI } from '../lib/api';
import { AllocationDelta } from '../components/AllocationDelta';
import { PriorityBreakdown } from '../components/PriorityBreakdown';
import { RevisedPlanBanner } from '../components/RevisedPlanBanner';
import { formatRelativeTime } from '../lib/utils';
import { formatScore, resourceCallsign, severityTier } from '../lib/ops';
import { ErrorBanner, EmptyState, Metric, PageHeader } from '../components/ui/chrome';
import { Card, CardBody, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';

const MapView = dynamic(() => import('../components/MapView').then((m) => m.MapView), { ssr: false });

export default function CommandCenter() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await snapshotAPI.get();
      setData(res.data);
      setError(null);
    } catch {
      setError('Unable to reach the operations API. Check that the backend is running on port 8000.');
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  if (!data && error) return <ErrorBanner message={error} />;
  if (!data) return <p className="text-slate-300">Loading operational state…</p>;

  const m = data.metrics || {};
  const zones = data.zones || [];
  const resources = data.resources || [];
  const incidents = data.incidents || [];
  const allocations = data.allocations || [];
  const zoneById = Object.fromEntries(zones.map((z: any) => [z.id, z]));
  const moves = data.delta?.moves || [];
  const simulation = (data.data_mode || 'SIMULATION') === 'SIMULATION';

  const assignmentRoutes = allocations
    .map((a: any) => {
      const res = resources.find((r: any) => r.id === a.resource_id);
      const zone = zoneById[a.zone_id];
      if (!res?.longitude || !zone?.longitude) return null;
      return {
        id: `a-${a.id}`,
        from: [res.longitude, res.latitude] as [number, number],
        to: [zone.longitude, zone.latitude] as [number, number],
        kind: 'assignment' as const,
        label: `${res.name} → ${zone.name}`,
      };
    })
    .filter(Boolean);

  const reallocationRoutes = moves
    .map((move: any, i: number) => {
      const from = zoneById[move.from_zone];
      const to = zoneById[move.to_zone];
      if (!from?.longitude || !to?.longitude) return null;
      return {
        id: `m-${i}`,
        from: [from.longitude, from.latitude] as [number, number],
        to: [to.longitude, to.latitude] as [number, number],
        kind: 'reallocation' as const,
        label: `${move.from_zone} → ${move.to_zone}`,
      };
    })
    .filter(Boolean);

  return (
    <div className="space-y-5">
      {error && <ErrorBanner message={error} />}
      <PageHeader
        kicker="CODECOMMIT"
        title="Emergency Resource Command Center"
        description="Understand the incident. Optimize the response. Re-plan when reality changes."
        actions={
          (data.active_plan_id || data.last_plan_id) && (
            <div className="text-xs text-slate-500">
              {data.revised_plan?.pending ? 'Pending plan' : 'Active plan'} {data.active_plan_id || data.last_plan_id}
            </div>
          )
        }
      />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Metric label="Critical Zones" value={m.critical_zones} />
        <Metric label="Active Incidents" value={m.active_incidents} />
        <Metric label="Available Resources" value={m.available_resources} />
        <Metric label="Deployed Resources" value={m.deployed_resources} />
        <Metric label="Unmet Critical Demand" value={Math.round(m.unmet_critical_demand || 0)} />
        <Metric label="Response Coverage" value={`${m.response_coverage ?? 0}%`} />
      </div>

      <RevisedPlanBanner plan={data.revised_plan} delta={data.delta} explanation={data.explanation} onChanged={load} />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.7fr)_minmax(20rem,1fr)]">
        <MapView
          simulation={simulation}
          zones={zones.map((z: any) => ({
            id: z.id,
            latitude: z.latitude,
            longitude: z.longitude,
            label: `${z.name} · ${formatScore(z.priority_score)} / 100`,
            color: z.priority_score >= 80 ? '#ef4444' : z.priority_score >= 60 ? '#f97316' : '#38bdf8',
            critical: z.priority_score >= 80,
          }))}
          resources={resources.map((r: any) => ({
            id: r.id,
            latitude: r.latitude,
            longitude: r.longitude,
            label: `${resourceCallsign(r)} · ${(r.status || '').toUpperCase()}`,
            color: r.status === 'available' ? '#22c55e' : '#a855f7',
          }))}
          incidents={incidents.map((i: any) => {
            const z = zoneById[i.zone_id];
            return {
              id: i.id,
              latitude: z?.latitude,
              longitude: z?.longitude,
              label: `${i.incident_type || 'incident'} · ${i.zone_id}`,
              color: '#f43f5e',
            };
          })}
          routes={[...assignmentRoutes, ...reallocationRoutes]}
        />

        <Card className="max-h-[34rem] overflow-auto">
          <CardHeader>
            <CardTitle>Priority Queue</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3">
            {zones.length === 0 ? (
              <EmptyState title="No zones loaded" hint="Use Scenario Simulator → Load Scenario." />
            ) : (
              zones
                .slice()
                .sort((a: any, b: any) => b.priority_score - a.priority_score)
                .map((z: any) => {
                  const tier = severityTier(z.priority_score);
                  const change = (data.delta?.priority_changes || []).find((p: any) => p.zone_id === z.id);
                  const trend = change && change.before != null && Math.abs(change.after - change.before) >= 0.01
                    ? `${formatScore(change.before, 2)} → ${formatScore(change.after, 2)}`
                    : null;
                  return (
                    <div key={z.id} className={`rounded-md border p-3 ${tier.tone === 'critical' ? 'border-red-700 bg-red-950/40' : 'border-slate-800'}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-white">{z.name}</div>
                          <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-slate-400">
                            <span>Severity {formatScore(z.severity, 1)} / 10</span>
                            <span>Pop {z.population ?? '—'}</span>
                            <span>Deficit {z.priority_breakdown?.resource_deficit ?? '—'}</span>
                          </div>
                          {trend && <div className="mt-1 text-xs text-amber-300">Change {trend}</div>}
                        </div>
                        <PriorityBreakdown score={z.priority_score} breakdown={z.priority_breakdown} />
                      </div>
                    </div>
                  );
                })
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Current Response</CardTitle></CardHeader>
          <CardBody>
            {moves.length === 0 && !data.delta ? (
              <EmptyState title="No reallocation in the latest plan" hint="Inject an urgent report to generate a delta." />
            ) : (
              <AllocationDelta delta={data.delta} explanation={data.explanation} />
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader><CardTitle>Resource Status</CardTitle></CardHeader>
          <CardBody className="space-y-2">
            {resources.length === 0 ? (
              <EmptyState title="No resources in inventory" />
            ) : (
              resources.slice(0, 8).map((r: any) => {
                const alloc = allocations.find((a: any) => a.resource_id === r.id);
                return (
                  <div key={r.id} className="rounded-md border border-slate-800 p-2 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-white">{resourceCallsign(r)}</span>
                      <Badge tone={r.status === 'available' ? 'success' : r.status === 'unavailable' ? 'neutral' : 'info'}>
                        {(r.status || '').replace('_', ' ')}
                      </Badge>
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      {alloc?.from_zone_id ? `${alloc.from_zone_id} → ${alloc.zone_id}` : (r.current_zone_id || 'Unassigned')}
                      {r.eta_minutes ? ` · ${r.eta_minutes} min ETA` : ''}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      {(Array.isArray(r.capabilities) ? r.capabilities.join(', ') : r.type) || '—'}
                    </div>
                  </div>
                );
              })
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader><CardTitle>Live Activity</CardTitle></CardHeader>
          <CardBody className="space-y-2">
            {(data.audit || []).length === 0 ? (
              <EmptyState title="No activity yet" hint="Load a scenario to start the pipeline." />
            ) : (
              (data.audit || []).slice(0, 10).map((e: any) => (
                <div key={e.id} className="grid grid-cols-[4.5rem_1fr] gap-2 text-sm">
                  <div className="text-[11px] text-slate-500">{e.timestamp ? formatRelativeTime(e.timestamp) : '—'}</div>
                  <div>
                    <span className="font-medium text-sky-300">{e.agent || e.actor}</span>
                    <span className="text-slate-300"> · {e.description}</span>
                  </div>
                </div>
              ))
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
