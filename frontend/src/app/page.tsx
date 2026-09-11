'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useState } from 'react';
import { snapshotAPI } from '../lib/api';
import { AllocationDelta } from '../components/AllocationDelta';
import { PriorityBreakdown } from '../components/PriorityBreakdown';
import { formatRelativeTime } from '../lib/utils';
import { EmptyState, ErrorBanner } from '../components/Status';

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
  if (!data) return <div className="text-slate-300">Loading operational state…</div>;

  const m = data.metrics || {};
  const zones = data.zones || [];
  const resources = data.resources || [];
  const incidents = data.incidents || [];
  const pending = (data.tasks || []).filter((t: any) => t.status === 'pending');
  const moves = data.delta?.moves || [];
  const zoneById = Object.fromEntries(zones.map((z: any) => [z.id, z]));

  const routes = (data.allocations || [])
    .map((a: any) => {
      const res = resources.find((r: any) => r.id === a.resource_id);
      const zone = zoneById[a.zone_id];
      if (!res?.longitude || !zone?.longitude) return null;
      return { id: a.id, from: [res.longitude, res.latitude], to: [zone.longitude, zone.latitude] };
    })
    .filter(Boolean);

  return (
    <div className="space-y-6">
      {error && <ErrorBanner message={error} />}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-xs font-semibold tracking-[0.2em] text-slate-400">CODECOMMIT</div>
          <h1 className="text-2xl font-bold text-white">Emergency Resource Command Center</h1>
          <p className="text-sm text-slate-400">Understand the incident. Optimize the response. Re-plan when reality changes.</p>
        </div>
        {data.last_plan_id && <div className="text-xs text-slate-500">Active plan {data.last_plan_id}</div>}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Critical Zones" value={m.critical_zones} />
        <Stat label="Active Incidents" value={m.active_incidents} />
        <Stat label="Available Resources" value={m.available_resources} />
        <Stat label="Deployed Resources" value={m.deployed_resources} />
        <Stat label="Unmet Critical Demand" value={Math.round(m.unmet_critical_demand || 0)} />
        <Stat label="Response Coverage" value={`${m.response_coverage ?? 0}%`} />
      </div>

      <MapView
        zones={zones.map((z: any) => ({
          id: z.id,
          latitude: z.latitude,
          longitude: z.longitude,
          label: `${z.name} · response priority ${Number(z.priority_score || 0).toFixed(0)}`,
          color: z.priority_score >= 80 ? '#ef4444' : z.priority_score >= 60 ? '#f97316' : '#38bdf8',
        }))}
        resources={resources.map((r: any) => ({
          id: r.id,
          latitude: r.latitude,
          longitude: r.longitude,
          label: `${r.name} (${(r.status || '').toUpperCase()})`,
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
        routes={routes}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Priority Queue">
          {zones.length === 0 ? (
            <EmptyState title="No zones loaded" hint="Use Scenario Simulator → Load Scenario." />
          ) : (
            zones
              .slice()
              .sort((a: any, b: any) => b.priority_score - a.priority_score)
              .map((z: any) => (
                <div key={z.id} className="mb-3 border-b border-slate-800 pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{z.name}</div>
                      <div className="text-xs text-slate-400">Severity {Number(z.severity || 0).toFixed(1)} / 10</div>
                    </div>
                    <PriorityBreakdown score={z.priority_score} breakdown={z.priority_breakdown} />
                  </div>
                </div>
              ))
          )}
        </Panel>

        <Panel title="Replanning Alerts">
          {moves.length === 0 ? (
            <EmptyState title="No reallocation in the latest plan" hint="Inject an urgent report to generate a delta." />
          ) : (
            <AllocationDelta delta={data.delta} />
          )}
        </Panel>

        <Panel title="Resource Status">
          {resources.length === 0 ? (
            <EmptyState title="No resources in inventory" />
          ) : (
            resources.slice(0, 10).map((r: any) => (
              <div key={r.id} className="mb-2 flex justify-between text-sm">
                <span className="text-white">{r.name}</span>
                <span className="uppercase text-slate-400">{r.status}</span>
              </div>
            ))
          )}
        </Panel>

        <Panel title="Active Coordination">
          {pending.length === 0 ? (
            <EmptyState title="No actions awaiting approval" />
          ) : (
            pending.slice(0, 8).map((t: any) => (
              <div key={t.id} className="mb-2 text-sm">
                <span className="font-medium text-violet-300">{t.agency_id}</span>
                <span className="text-slate-300"> — {t.action}</span>
              </div>
            ))
          )}
        </Panel>
      </div>

      <Panel title="Live Activity">
        {(data.audit || []).length === 0 ? (
          <EmptyState title="No activity yet" hint="Load a scenario to start the pipeline." />
        ) : (
          (data.audit || []).slice(0, 12).map((e: any) => (
            <div key={e.id} className="mb-2 flex gap-3 text-sm">
              <div className="w-16 shrink-0 text-xs text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</div>
              <div>
                <span className="font-medium text-blue-300">{e.agent || e.actor}</span>
                <span className="text-slate-300"> · {e.description}</span>
              </div>
            </div>
          ))
        )}
      </Panel>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-bold text-white">{value ?? 0}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      {children}
    </section>
  );
}
