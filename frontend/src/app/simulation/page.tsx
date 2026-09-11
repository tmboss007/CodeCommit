'use client';

import { useState } from 'react';
import { simulationAPI } from '../../lib/api';
import { AllocationDelta } from '../../components/AllocationDelta';
import { ErrorBanner, PageHeader } from '../../components/ui/chrome';
import { Button } from '../../components/ui/button';
import { Card, CardBody, CardHeader, CardTitle } from '../../components/ui/card';

const ACTIONS = [
  { id: 'load', label: 'Load Scenario', run: simulationAPI.loadDemo, variant: 'primary' as const },
  { id: 'reset', label: 'Reset Scenario', run: simulationAPI.reset, variant: 'secondary' as const },
  { id: 'urgent', label: 'Inject Urgent Report', run: simulationAPI.injectUrgent, variant: 'danger' as const },
  { id: 'route', label: 'Block Route', run: simulationAPI.blockRoute, variant: 'outline' as const },
  { id: 'disable', label: 'Disable Resource', run: simulationAPI.disableResource, variant: 'outline' as const },
  { id: 'demand', label: 'Increase Demand', run: simulationAPI.increaseDemand, variant: 'outline' as const },
  { id: 'replan', label: 'Run Replan', run: simulationAPI.runReplan, variant: 'outline' as const },
];

export default function ScenarioSimulatorPage() {
  const [busy, setBusy] = useState<string | null>(null);
  const [output, setOutput] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setError(null);
    try {
      const res = await fn();
      setOutput(res.data);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'The scenario action failed. Confirm the API is running and try again.');
    } finally {
      setBusy(null);
    }
  };

  const plan = output?.plan || output;
  const delta = plan?.delta || output?.delta;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Scenario Simulator"
        description="Deterministic five-zone exercise. Weather, satellite, and routing remain simulation data."
      />
      <div className="rounded-md border border-amber-700 bg-amber-950/40 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-amber-200">
        Simulation mode — actions change the local operational database
      </div>
      <div className="flex flex-wrap gap-2">
        {ACTIONS.map((a) => (
          <Button key={a.id} variant={a.variant} disabled={!!busy} onClick={() => run(a.id, a.run)}>
            {busy === a.id ? 'Working…' : a.label}
          </Button>
        ))}
      </div>
      {error && <ErrorBanner message={error} />}
      {delta && (
        <Card>
          <CardHeader><CardTitle>Allocation delta</CardTitle></CardHeader>
          <CardBody>
            <AllocationDelta delta={delta} />
          </CardBody>
        </Card>
      )}
      {output && (
        <pre className="max-h-[420px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
          {JSON.stringify(output, null, 2)}
        </pre>
      )}
    </div>
  );
}
