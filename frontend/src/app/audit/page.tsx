'use client';

import { Fragment, useEffect, useState } from 'react';
import { snapshotAPI } from '../../lib/api';
import { EmptyState, ErrorBanner } from '../../components/Status';

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
      <h1 className="mb-1 text-2xl font-bold text-white">Audit</h1>
      <p className="mb-4 text-sm text-slate-400">Immutable history of incident analysis, allocation, approval, and replanning.</p>
      {error && <ErrorBanner message={error} />}
      {events.length === 0 && !error ? (
        <EmptyState title="Audit log is empty" hint="Operational actions will appear here." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="p-2">Time</th>
                <th className="p-2">Type</th>
                <th className="p-2">Actor</th>
                <th className="p-2">Service</th>
                <th className="p-2">Description</th>
                <th className="p-2">Corr</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <Fragment key={e.id}>
                  <tr className="cursor-pointer border-t border-slate-800" onClick={() => setOpen(open === e.id ? null : e.id)}>
                    <td className="p-2 text-slate-400">{new Date(e.timestamp).toLocaleString()}</td>
                    <td className="p-2">{e.event_type}</td>
                    <td className="p-2">{e.actor}</td>
                    <td className="p-2">{e.agent || '—'}</td>
                    <td className="p-2 text-slate-200">{e.description}</td>
                    <td className="p-2 text-xs text-slate-500">{e.correlation_id}</td>
                  </tr>
                  {open === e.id && (
                    <tr className="bg-slate-950/50">
                      <td colSpan={6} className="p-3 text-xs text-slate-400">
                        <div>Reason: {e.reason || e.description}</div>
                        <pre className="mt-2 overflow-auto">{JSON.stringify({ previous_state: e.previous_state, new_state: e.new_state }, null, 2)}</pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
