'use client';

import { useState } from 'react';
import { simulationAPI } from '../../lib/api';
import { AllocationDelta } from '../../components/AllocationDelta';
import { formatEventLabel } from '../../lib/ops';
import { useOps } from '../../lib/ops-runtime';
import { ErrorBanner, PageHeader, Section } from '../../components/ui/chrome';
import { Button } from '../../components/ui/button';

const ACTIONS = [
  { id: 'load', label: 'Load scenario', run: simulationAPI.loadDemo, variant: 'primary' as const },
  { id: 'reset', label: 'Reset', run: simulationAPI.reset, variant: 'secondary' as const },
  { id: 'urgent', label: 'Inject urgent report', run: simulationAPI.injectUrgent, variant: 'danger' as const },
  { id: 'route', label: 'Block route', run: simulationAPI.blockRoute, variant: 'outline' as const },
  { id: 'disable', label: 'Disable resource', run: simulationAPI.disableResource, variant: 'outline' as const },
  { id: 'demand', label: 'Increase demand', run: simulationAPI.increaseDemand, variant: 'outline' as const },
  { id: 'replan', label: 'Run replan', run: simulationAPI.runReplan, variant: 'outline' as const },
];

export default function ScenarioSimulatorPage() {
  const { data, refresh } = useOps();
  const [busy, setBusy] = useState<string | null>(null);
  const [output, setOutput] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setError(null);
    try {
      const res = await fn();
      setOutput(res.data);
      await refresh(true);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'The scenario action failed. Confirm the API is running and try again.');
    } finally {
      setBusy(null);
    }
  };

  const plan = output?.plan || output;
  const delta = plan?.delta || output?.delta || data?.delta;
  const zones = data?.zones?.length || 0;
  const incidents = data?.incidents?.length || 0;
  const resources = data?.resources?.length || 0;
  const currentPlan = data?.active_plan_id || data?.last_plan_id || 'None';
  const events = data?.audit || [];

  return (
    <div className="space-y-8">
      <PageHeader
        title="Scenario Simulator"
        description="Five-zone exercise. Weather, satellite, and routing remain simulation data."
      />
      <p className="text-sm text-muted">Simulation mode — actions change the local operational database. External feeds are not live.</p>

      <Section title="Current scenario">
        <div className="grid grid-cols-2 border border-line bg-white sm:grid-cols-4">
          {[
            ['Zones', zones],
            ['Incidents', incidents],
            ['Resources', resources],
            ['Current plan', currentPlan],
          ].map(([label, value]) => (
            <div key={String(label)} className="border-line px-4 py-3 sm:border-l sm:first:border-l-0">
              <div className="text-[12px] text-muted">{label}</div>
              <div className="mt-1 text-sm font-semibold text-ink">{value}</div>
            </div>
          ))}
        </div>
      </Section>

      <div className="flex flex-wrap gap-2">
        {ACTIONS.map((a) => (
          <Button key={a.id} variant={a.variant} disabled={!!busy} onClick={() => run(a.id, a.run)}>
            {busy === a.id ? 'Working…' : a.label}
          </Button>
        ))}
      </div>
      {error && <ErrorBanner message={error} />}

      <div className="grid gap-8 lg:grid-cols-12">
        <Section title="Plan delta" className="lg:col-span-6">
          <AllocationDelta delta={delta} allocations={data?.allocations} />
        </Section>
        <Section title="Event timeline" className="lg:col-span-6">
          {events.length === 0 ? (
            <p className="text-sm text-muted">No events yet. Load a scenario to populate the timeline.</p>
          ) : (
            <ul className="max-h-[28rem] overflow-auto">
              {events.slice(0, 40).map((e: any) => (
                <li key={e.id} className="border-b border-line py-2 text-sm">
                  <div className="text-[12px] tabular-nums text-muted">{e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour12: false }) : '—'}</div>
                  <div className="font-semibold">{formatEventLabel(e.event_type)}</div>
                  <div className="text-muted">{e.description}</div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}
