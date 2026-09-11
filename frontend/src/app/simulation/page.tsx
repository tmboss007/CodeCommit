'use client';

import { useState } from 'react';
import { simulationAPI } from '../../lib/api';
import { AllocationDelta } from '../../components/AllocationDelta';
import { ErrorBanner } from '../../components/Status';

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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Scenario Simulator</h1>
        <p className="text-sm text-slate-400">
          Exercise allocation and replanning with a deterministic five-zone scenario. Weather, satellite, and routing feeds remain simulation data.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Btn busy={busy} id="load" onClick={() => run('load', simulationAPI.loadDemo)}>Load Scenario</Btn>
        <Btn busy={busy} id="reset" onClick={() => run('reset', simulationAPI.reset)}>Reset Scenario</Btn>
        <Btn busy={busy} id="urgent" onClick={() => run('urgent', simulationAPI.injectUrgent)}>Inject Urgent Report</Btn>
        <Btn busy={busy} id="route" onClick={() => run('route', simulationAPI.blockRoute)}>Block Route</Btn>
        <Btn busy={busy} id="disable" onClick={() => run('disable', simulationAPI.disableResource)}>Disable Resource</Btn>
        <Btn busy={busy} id="demand" onClick={() => run('demand', simulationAPI.increaseDemand)}>Increase Demand</Btn>
        <Btn busy={busy} id="replan" onClick={() => run('replan', simulationAPI.runReplan)}>Run Replan</Btn>
      </div>
      {error && <ErrorBanner message={error} />}
      {delta && (
        <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
          <h2 className="mb-3 font-semibold text-white">Allocation delta</h2>
          <AllocationDelta delta={delta} />
        </section>
      )}
      {output && (
        <pre className="max-h-[420px] overflow-auto rounded border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
          {JSON.stringify(output, null, 2)}
        </pre>
      )}
    </div>
  );
}

function Btn({ children, onClick, busy, id }: { children: React.ReactNode; onClick: () => void; busy: string | null; id: string }) {
  return (
    <button
      onClick={onClick}
      disabled={!!busy}
      className="rounded bg-blue-600 px-3 py-2 text-sm text-white disabled:opacity-50"
    >
      {busy === id ? 'Working…' : children}
    </button>
  );
}
