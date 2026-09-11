'use client';

import { useCallback, useEffect, useState } from 'react';
import { coordinationAPI, snapshotAPI } from '../../lib/api';
import { EmptyState, ErrorBanner } from '../../components/Status';

export default function CoordinationPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const snap = await snapshotAPI.get();
    setTasks(snap.data.tasks || []);
    setAllocations(snap.data.allocations || []);
  }, []);

  useEffect(() => {
    load().catch(() => setError('Could not load coordination tasks.'));
  }, [load]);

  const act = async (id: string, kind: 'approve' | 'reject') => {
    try {
      if (kind === 'approve') await coordinationAPI.approveTask(id);
      else await coordinationAPI.rejectTask(id);
      setMessage(kind === 'approve' ? 'Approved — allocation and resource state updated.' : 'Rejected — allocation was not applied.');
      setError(null);
      await load();
    } catch {
      setError('The decision could not be saved. Refresh and try again.');
    }
  };

  const groups = ['pending', 'approved', 'in_progress', 'completed', 'rejected'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Coordination</h1>
        <p className="text-sm text-slate-400">High-impact deployments require approval. Reject leaves resource assignment unchanged.</p>
      </div>
      {message && <div className="text-sm text-emerald-300">{message}</div>}
      {error && <ErrorBanner message={error} />}
      {tasks.length === 0 && <EmptyState title="No agency tasks" hint="Load a scenario to generate an allocation plan." />}
      {groups.map((status) => {
        const items = tasks.filter((t) => t.status === status);
        if (!items.length && status !== 'pending') return null;
        return (
          <section key={status} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase text-slate-400">
              {status === 'pending' ? 'Approval required' : status.replace('_', ' ')}
            </h2>
            {items.length === 0 && <div className="text-sm text-slate-500">None</div>}
            {items.map((t) => {
              const alloc = allocations.find((a) => a.id === t.allocation_id);
              return (
                <div key={t.id} className="mb-3 rounded border border-slate-800 p-3">
                  <div className="text-sm font-medium text-violet-300">{t.agency_id}</div>
                  <div className="text-sm text-white">{t.action}</div>
                  {alloc && (
                    <div className="mt-2 text-xs text-slate-400">
                      {alloc.from_zone_id ? `${alloc.from_zone_id} → ` : ''}
                      {alloc.zone_id} · {alloc.reason}
                    </div>
                  )}
                  {t.status === 'pending' && (
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => act(t.id, 'approve')} className="rounded bg-emerald-600 px-3 py-1 text-sm">Approve</button>
                      <button onClick={() => act(t.id, 'reject')} className="rounded bg-red-700 px-3 py-1 text-sm">Reject</button>
                    </div>
                  )}
                </div>
              );
            })}
          </section>
        );
      })}
    </div>
  );
}
