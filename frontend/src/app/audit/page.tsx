'use client';

import { useEffect, useState } from 'react';
import { snapshotAPI } from '../../lib/api';
import { kindForActor } from '../../lib/ops';
import { EmptyState, ErrorBanner, PageHeader } from '../../components/ui/chrome';
import { Badge } from '../../components/ui/badge';

export default function AuditPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    snapshotAPI.get()
      .then((r) => setEvents(r.data.audit || []))
      .catch(() => setError('Could not load the audit log.'));
  }, []);

  return (
    <div>
      <PageHeader title="Audit" description="Operational timeline of analysis, allocation, approval, and replanning. Expand an event for previous and new state." />
      {error && <ErrorBanner message={error} />}
      {events.length === 0 && !error ? (
        <EmptyState title="Audit log is empty" hint="Operational actions will appear here." />
      ) : (
        <ol className="relative space-y-3 border-l border-slate-800 pl-5">
          {events.map((e) => {
            const expanded = open === e.id;
            return (
              <li key={e.id}>
                <span aria-hidden className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border border-slate-500 bg-slate-900" />
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setOpen(expanded ? null : e.id)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-900 p-3 text-left hover:border-slate-600"
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <span>{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</span>
                    <Badge tone="info">{e.event_type}</Badge>
                    <Badge>{kindForActor(e.agent)}</Badge>
                    <span>{e.agent || e.actor}</span>
                    {e.correlation_id && <span>corr {e.correlation_id}</span>}
                  </div>
                  <p className="mt-1 text-sm text-slate-100">{e.description}</p>
                  <p className="mt-1 text-xs text-slate-500">Reason: {e.reason || e.description}</p>
                </button>
                {expanded && (
                  <div className="mt-2 grid gap-3 rounded-md border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300 md:grid-cols-2">
                    <pre className="overflow-auto whitespace-pre-wrap">Previous state{'\n'}{JSON.stringify(e.previous_state ?? null, null, 2)}</pre>
                    <pre className="overflow-auto whitespace-pre-wrap">New state{'\n'}{JSON.stringify(e.new_state ?? null, null, 2)}</pre>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
