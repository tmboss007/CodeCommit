'use client';

import dynamic from 'next/dynamic';
import { AllocationDelta } from '../components/AllocationDelta';
import { PriorityBreakdown } from '../components/PriorityBreakdown';
import { RevisedPlanBanner } from '../components/RevisedPlanBanner';
import { affectedInZone, deficitLabel, formatCount, formatEventLabel, formatScore, resourceCallsign, zoneLetter } from '../lib/ops';
import { useOps } from '../lib/ops-runtime';
import { ErrorBanner, EmptyState, MetricStrip, PageHeader, Section } from '../components/ui/chrome';
import { Table, THead, Th, Td } from '../components/ui/table';

const MapView = dynamic(() => import('../components/MapView').then((m) => m.MapView), { ssr: false });

function clock(ts?: string) {
  if (!ts) return '—';
  return new Date(ts).toLocaleTimeString([], { hour12: false });
}

export default function CommandCenter() {
  const { data, error, refresh } = useOps();

  if (!data && error) return <ErrorBanner message={error} />;
  if (!data) return <p className="text-muted">Loading operational state…</p>;

  const m = data.metrics || {};
  const zones: any[] = data.zones || [];
  const resources: any[] = data.resources || [];
  const incidents: any[] = data.incidents || [];
  const allocations: any[] = data.allocations || [];
  const zoneById = Object.fromEntries(zones.map((z: any) => [z.id, z]));
  const moves = data.delta?.moves || [];
  const simulation = (data.data_mode || 'SIMULATION') === 'SIMULATION';
  const highPriority = zones.filter((z: any) => (z.priority_score || 0) >= 60 && (z.priority_score || 0) < 80).length;

  const needs: any[] = data.needs || [];
  const priChange = (zoneId: string) =>
    (data.delta?.priority_changes || []).find((p: any) => p.zone_id === zoneId && p.before != null && Math.abs(p.after - p.before) >= 0.01);

  const assignmentRoutes = allocations
    .map((a: any) => {
      const res = resources.find((r: any) => r.id === a.resource_id);
      const to = zoneById[a.zone_id];
      const fromZone = zoneById[a.from_zone_id];
      if (!res?.longitude || !to?.longitude) return null;
      const from: [number, number] = fromZone?.longitude
        ? [fromZone.longitude, fromZone.latitude]
        : [res.longitude, res.latitude];
      const callsign = resourceCallsign(res);
      const shortPath = `${zoneLetter(a.from_zone_id || res.current_zone_id)} → ${zoneLetter(a.zone_id)}`;
      const eta = a.eta_minutes || res.eta_minutes;
      return {
        id: `a-${a.id}`,
        from,
        to: [to.longitude, to.latitude] as [number, number],
        kind: 'assignment' as const,
        callsign,
        shortPath,
        etaLabel: eta ? `${eta} min` : '—',
        rows: [
          { label: 'Resource', value: callsign },
          { label: 'From', value: fromZone?.name || a.from_zone_id || '—' },
          { label: 'To', value: to.name || a.zone_id },
          { label: 'ETA', value: eta ? `${eta} min` : '—' },
          { label: 'Plan', value: a.plan_id || data.active_plan_id || data.last_plan_id || '—' },
          { label: 'Reason', value: a.reason || 'Assignment in current plan' },
        ],
      };
    })
    .filter(Boolean);

  const reallocationRoutes = moves
    .map((move: any, i: number) => {
      const from = zoneById[move.from_zone];
      const to = zoneById[move.to_zone];
      const res = resources.find((r: any) => r.id === move.resource_id);
      if (!from?.longitude || !to?.longitude) return null;
      const callsign = resourceCallsign(res || { id: move.resource_id, name: move.name });
      const alloc = allocations.find((a: any) => a.resource_id === move.resource_id);
      const change = priChange(move.to_zone);
      const reason = change
        ? `${to.name || move.to_zone} priority ${formatScore(change.before, 2)} → ${formatScore(change.after, 2)}`
        : (move.reason || data.explanation || 'Reallocation in revised plan');
      const eta = alloc?.eta_minutes || res?.eta_minutes;
      return {
        id: `m-${i}`,
        from: [from.longitude, from.latitude] as [number, number],
        to: [to.longitude, to.latitude] as [number, number],
        kind: 'reallocation' as const,
        callsign,
        shortPath: `${zoneLetter(move.from_zone)} → ${zoneLetter(move.to_zone)}`,
        etaLabel: 'REALLOCATION',
        rows: [
          { label: 'Resource', value: callsign },
          { label: 'From', value: from.name || move.from_zone },
          { label: 'To', value: to.name || move.to_zone },
          { label: 'ETA', value: eta ? `${eta} min` : '—' },
          { label: 'Plan', value: alloc?.plan_id || data.revised_plan?.plan_id || data.last_plan_id || '—' },
          { label: 'Reason', value: reason },
        ],
      };
    })
    .filter(Boolean);

  return (
    <div className="space-y-8">
      {error && <ErrorBanner message={error} />}
      <PageHeader
        title="Command Center"
        actions={
          (data.active_plan_id || data.last_plan_id) && (
            <div className="text-[13px] text-muted">
              {data.revised_plan?.pending ? 'Pending plan' : 'Active plan'} {data.active_plan_id || data.last_plan_id}
            </div>
          )
        }
      />

      <MetricStrip
        items={[
          { label: 'Critical zones', value: m.critical_zones },
          { label: 'High-priority zones', value: highPriority },
          { label: 'Active incidents', value: m.active_incidents },
          { label: 'Available resources', value: m.available_resources },
          { label: 'Deployed resources', value: m.deployed_resources },
          { label: 'Response coverage', value: `${m.response_coverage ?? 0}%` },
        ]}
      />
      <DataSources sources={data.data_sources} />

      <RevisedPlanBanner
        plan={data.revised_plan}
        delta={data.delta}
        explanation={data.explanation}
        allocations={allocations}
        onChanged={refresh}
      />

      <div className="grid gap-8 xl:grid-cols-12">
        <Section title="Map" className="xl:col-span-8">
          <MapView
            simulation={simulation}
            zones={zones.map((z: any) => {
              const zoneNeeds = needs.filter((n: any) => n.zone_id === z.id).slice(0, 4)
                .map((n: any) => `${n.resource_type} ${n.quantity_required}${n.unit ? ` ${n.unit}` : ''}`)
                .join('; ');
              const assigned = allocations
                .filter((a: any) => a.zone_id === z.id)
                .map((a: any) => resourceCallsign(resources.find((r: any) => r.id === a.resource_id) || { id: a.resource_id }))
                .join(', ');
              return {
                id: z.id,
                latitude: z.latitude,
                longitude: z.longitude,
                label: z.name,
                color: z.priority_score >= 80 ? '#B42318' : z.priority_score >= 60 ? '#C75B12' : '#243B53',
                critical: z.priority_score >= 80,
                high: z.priority_score >= 60 && z.priority_score < 80,
                rows: [
                  { label: 'Zone', value: z.name },
                  { label: 'Priority', value: formatScore(z.priority_score, 2) },
                  { label: 'Severity', value: `${formatScore(z.severity, 1)} / 10` },
                  { label: 'Affected', value: formatCount(affectedInZone(incidents, z.id)) },
                  { label: 'Needs', value: zoneNeeds || '—' },
                  { label: 'Assigned', value: assigned || '—' },
                ],
              };
            })}
            resources={resources.map((r: any) => {
              const alloc = allocations.find((a: any) => a.resource_id === r.id);
              const cap = Array.isArray(r.capabilities) ? r.capabilities.join(', ') : (r.type || '—');
              return {
                id: r.id,
                latitude: r.latitude,
                longitude: r.longitude,
                label: resourceCallsign(r),
                color: r.status === 'available' ? '#176B47' : '#59636E',
                rows: [
                  { label: 'Resource', value: resourceCallsign(r) },
                  { label: 'Agency', value: r.agency_id || '—' },
                  { label: 'Status', value: (r.status || '—').replace('_', ' ').toUpperCase() },
                  { label: 'From', value: zoneById[alloc?.from_zone_id]?.name || alloc?.from_zone_id || '—' },
                  { label: 'To', value: zoneById[alloc?.zone_id || r.current_zone_id]?.name || alloc?.zone_id || r.current_zone_id || '—' },
                  { label: 'ETA', value: (alloc?.eta_minutes || r.eta_minutes) ? `${alloc?.eta_minutes || r.eta_minutes} min` : '—' },
                  { label: 'Capability', value: cap },
                ],
              };
            })}
            incidents={incidents.map((i: any) => {
              const z = zoneById[i.zone_id];
              return {
                id: i.id,
                latitude: z?.latitude,
                longitude: z?.longitude,
                label: `${i.incident_type || 'incident'} · ${i.zone_id}`,
                color: '#7A2634',
                rows: [
                  { label: 'Incident', value: i.incident_type || i.id },
                  { label: 'Zone', value: z?.name || i.zone_id },
                  { label: 'Affected', value: formatCount(i.affected_population) },
                  { label: 'Status', value: i.status || '—' },
                ],
              };
            })}
            routes={[...assignmentRoutes, ...reallocationRoutes] as any}
          />
        </Section>

        <Section title="Priority queue" className="xl:col-span-4">
          {zones.length === 0 ? (
            <EmptyState title="No zones loaded" hint="Use Scenario Simulator → Load Scenario." />
          ) : (
            <ol className="max-h-[34rem] overflow-auto border-y border-line">
              {zones
                .slice()
                .sort((a: any, b: any) => b.priority_score - a.priority_score)
                .map((z: any, idx: number) => {
                  const change = (data.delta?.priority_changes || []).find((p: any) => p.zone_id === z.id);
                  const trend = change && change.before != null && Math.abs(change.after - change.before) >= 0.01
                    ? `${formatScore(change.before, 2)} → ${formatScore(change.after, 2)}`
                    : null;
                  const deficit = z.priority_breakdown?.resource_deficit;
                  return (
                    <li key={z.id} className="flex gap-3 border-b border-line py-3 last:border-b-0">
                      <div className="w-7 text-[13px] tabular-nums text-muted">{String(idx + 1).padStart(2, '0')}</div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-baseline justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate font-medium text-ink">{z.id}</div>
                            <div className="truncate text-[13px] text-muted">{z.name}</div>
                          </div>
                          <PriorityBreakdown score={z.priority_score} />
                        </div>
                        <div className="mt-1 text-[13px] text-muted">
                          Affected {formatCount(affectedInZone(incidents, z.id))}
                          {' · Deficit '}
                          {deficitLabel(deficit)}
                        </div>
                        {trend && <div className="mt-1 text-[13px] text-ink">{trend}</div>}
                      </div>
                    </li>
                  );
                })}
            </ol>
          )}
        </Section>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        <Section title="Current response" className="lg:col-span-4">
          {moves.length === 0 && !data.delta && allocations.length === 0 ? (
            <EmptyState title="No reallocation in the latest plan" hint="Inject an urgent report to generate a delta." />
          ) : (
            <AllocationDelta delta={data.delta} explanation={data.explanation} allocations={allocations} />
          )}
        </Section>
        <Section title="Resource status" className="lg:col-span-5">
          {resources.length === 0 ? (
            <EmptyState title="No resources in inventory" />
          ) : (
            <Table>
              <THead>
                <tr>
                  <Th>Resource</Th>
                  <Th>Status</Th>
                  <Th>From</Th>
                  <Th>To</Th>
                  <Th>ETA</Th>
                  <Th>Capability</Th>
                </tr>
              </THead>
              <tbody>
                {resources.slice(0, 10).map((r: any) => {
                  const alloc = allocations.find((a: any) => a.resource_id === r.id);
                  return (
                    <tr key={r.id}>
                      <Td className="font-medium">{resourceCallsign(r)}</Td>
                      <Td className="uppercase">{(r.status || '').replace('_', ' ')}</Td>
                      <Td>{alloc?.from_zone_id || '—'}</Td>
                      <Td>{alloc?.zone_id || r.current_zone_id || '—'}</Td>
                      <Td>{r.eta_minutes ? `${r.eta_minutes} min` : '—'}</Td>
                      <Td>{(Array.isArray(r.capabilities) ? r.capabilities.join(', ') : r.type) || '—'}</Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </Section>
        <Section title="Live activity" className="lg:col-span-3">
          {(data.audit || []).length === 0 ? (
            <EmptyState title="No activity yet" hint="Load a scenario to start the pipeline." />
          ) : (
            <ul>
              {(data.audit || []).slice(0, 12).map((e: any) => (
                <li key={e.id} className="border-b border-line py-2 last:border-b-0">
                  <div className="text-[12px] tabular-nums text-muted">{clock(e.timestamp)}</div>
                  <div className="text-[13px] font-semibold text-ink">{formatEventLabel(e.event_type)}</div>
                  <div className="text-[13px] text-muted">{e.description}</div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}

function DataSources({ sources }: { sources?: Array<{ label: string; mode: string }> }) {
  const rows = sources && sources.length
    ? sources
    : [
        { label: 'GDACS', mode: 'SIMULATION' },
        { label: 'IMD', mode: 'SIMULATION' },
        { label: 'MOSDAC', mode: 'SIMULATION' },
        { label: 'Routing', mode: 'SIMULATION' },
      ];
  return (
    <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 border-b border-line pb-3 text-[12px] text-muted">
      <span className="font-semibold uppercase tracking-[0.06em] text-ink">Data sources</span>
      {rows.map((row) => (
        <span key={row.label} className="tabular-nums">
          {row.label} {row.mode}
        </span>
      ))}
    </div>
  );
}
