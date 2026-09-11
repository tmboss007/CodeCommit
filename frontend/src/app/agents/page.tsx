'use client';

import { useEffect, useState } from 'react';
import { snapshotAPI } from '../../lib/api';
import { PIPELINE, kindForActor, pipelineStatus } from '../../lib/ops';
import { EmptyState, ErrorBanner, PageHeader } from '../../components/ui/chrome';
import { Badge } from '../../components/ui/badge';
import { Card, CardBody } from '../../components/ui/card';

const statusTone = {
  RUNNING: 'warning',
  COMPLETED: 'success',
  WAITING: 'neutral',
  FAILED: 'critical',
} as const;

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
      <PageHeader
        title="Agents"
        description="Agents interpret reports and coordinate agencies. Decision services score needs, priority, and allocations. Status is derived from stored events — not simulated typing."
      />
      <div className="mb-5 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        {PIPELINE.map((p) => {
          const status = pipelineStatus(events, p.match);
          return (
            <Card key={p.label}>
              <CardBody>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">{p.kind}</div>
                <div className="mt-1 font-medium text-white">{p.label}</div>
                <div className="mt-2">
                  <Badge tone={statusTone[status]}>{status}</Badge>
                </div>
              </CardBody>
            </Card>
          );
        })}
      </div>
      {error && <ErrorBanner message={error} />}
      {events.length === 0 && !error ? (
        <EmptyState title="No pipeline events yet" hint="Load a scenario or submit an incident." />
      ) : (
        <div className="space-y-2">
          {events.map((e) => (
            <div key={e.id} className="grid grid-cols-[80px_1fr] gap-3 rounded-lg border border-slate-800 bg-slate-900 p-3 text-sm">
              <div className="text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-sky-300">{e.agent || e.actor}</span>
                  <Badge>{kindForActor(e.agent)}</Badge>
                  <Badge tone="info">{e.event_type}</Badge>
                </div>
                <div className="mt-1 text-slate-200">{e.description}</div>
                {e.correlation_id && <div className="text-xs text-slate-500">corr {e.correlation_id}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
