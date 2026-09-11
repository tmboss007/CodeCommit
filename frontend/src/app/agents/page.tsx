'use client';

import { useEffect, useState } from 'react';
import { snapshotAPI } from '../../lib/api';
import { EmptyState, ErrorBanner, kindForActor } from '../../components/Status';

const PIPELINE = [
  { match: 'Situation', label: 'Situation Agent', kind: 'Agent' },
  { match: 'Needs', label: 'Needs Assessment', kind: 'Decision Service' },
  { match: 'Priority', label: 'Priority', kind: 'Decision Service' },
  { match: 'Duplicate', label: 'Duplicate Detection', kind: 'Agent' },
  { match: 'Optimization', label: 'Optimization Engine', kind: 'Decision Service' },
  { match: 'Coordination', label: 'Coordination Agent', kind: 'Agent' },
  { match: 'Replanning', label: 'Replanning', kind: 'Decision Service' },
];

export default function AgentsPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () =>
      snapshotAPI.get()
        .then((r) => setEvents(r.data.audit || []))
        .catch(() => setError('Could not load activity events.'));
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, []);

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-white">Agents</h1>
      <p className="mb-4 text-sm text-slate-400">
        Events are stored by the backend. Interpretation components are agents; scoring, needs, and allocation are decision services.
      </p>
      <div className="mb-4 flex flex-wrap gap-2 text-xs">
        {PIPELINE.map((p) => (
          <span key={p.label} className="rounded border border-slate-700 px-2 py-1 text-slate-300">
            {p.label} · {p.kind}
          </span>
        ))}
      </div>
      {error && <ErrorBanner message={error} />}
      {events.length === 0 && !error ? (
        <EmptyState title="No pipeline events yet" hint="Load a scenario or submit an incident." />
      ) : (
        <div className="space-y-2">
          {events.map((e) => (
            <div key={e.id} className="grid grid-cols-[80px_1fr] gap-3 rounded border border-slate-800 bg-slate-900 p-3 text-sm">
              <div className="text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</div>
              <div>
                <div className="font-medium text-blue-300">
                  {e.agent || e.actor} · {kindForActor(e.agent)} · {e.event_type}
                </div>
                <div className="text-slate-200">{e.description}</div>
                {e.correlation_id && <div className="text-xs text-slate-500">corr {e.correlation_id}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
