'use client';

import { useEffect, useMemo, useState } from 'react';
import { snapshotAPI } from '../../lib/api';
import { EmptyState, ErrorBanner } from '../../components/Status';

const STATUSES = ['available', 'reserved', 'en_route', 'deployed', 'unavailable', 'maintenance'];

export default function ResourcesPage() {
  const [resources, setResources] = useState<any[]>([]);
  const [status, setStatus] = useState('');
  const [type, setType] = useState('');
  const [agency, setAgency] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    snapshotAPI.get()
      .then((r) => setResources(r.data.resources || []))
      .catch(() => setError('Could not load resource inventory.'));
  }, []);

  const filtered = useMemo(
    () => resources.filter((r) => (!status || r.status === status) && (!type || r.type === type) && (!agency || r.agency_id === agency)),
    [resources, status, type, agency]
  );

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold text-white">Resources</h1>
      <p className="mb-4 text-sm text-slate-400">Live inventory and assignment state. Status values are backend-owned.</p>
      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      <div className="mb-4 flex flex-wrap gap-2">
        <select className="rounded bg-slate-800 p-2" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.toUpperCase()}</option>
          ))}
        </select>
        <select className="rounded bg-slate-800 p-2" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option>
          {Array.from(new Set(resources.map((r) => r.type))).map((t) => (
            <option key={t as string}>{t as string}</option>
          ))}
        </select>
        <select className="rounded bg-slate-800 p-2" value={agency} onChange={(e) => setAgency(e.target.value)}>
          <option value="">All agencies</option>
          {Array.from(new Set(resources.map((r) => r.agency_id))).map((t) => (
            <option key={t as string}>{t as string}</option>
          ))}
        </select>
      </div>
      {filtered.length === 0 ? (
        <EmptyState title="No resources match these filters" hint="Load a scenario or clear filters." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="p-2">ID</th>
                <th className="p-2">Type</th>
                <th className="p-2">Agency</th>
                <th className="p-2">Capability</th>
                <th className="p-2">Location</th>
                <th className="p-2">Status</th>
                <th className="p-2">Capacity</th>
                <th className="p-2">Assignment</th>
                <th className="p-2">ETA</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} className="border-t border-slate-800">
                  <td className="p-2 text-slate-400">{r.id}</td>
                  <td className="p-2 text-white">{r.type}</td>
                  <td className="p-2">{r.agency_id}</td>
                  <td className="p-2">{Array.isArray(r.capabilities) ? r.capabilities.join(', ') : '—'}</td>
                  <td className="p-2">{r.latitude && r.longitude ? `${Number(r.latitude).toFixed(3)}, ${Number(r.longitude).toFixed(3)}` : '—'}</td>
                  <td className="p-2 uppercase">{r.status}</td>
                  <td className="p-2">{r.quantity} {r.unit}</td>
                  <td className="p-2">{r.current_zone_id || '—'}</td>
                  <td className="p-2">{r.eta_minutes ? `${r.eta_minutes} min` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
