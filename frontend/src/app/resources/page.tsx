'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { resourcesAPI, snapshotAPI } from '../../lib/api';
import { apiError, resourceCallsign } from '../../lib/ops';
import { EmptyState, ErrorBanner, Notice, PageHeader } from '../../components/ui/chrome';
import { Label, Select, Input } from '../../components/ui/input';
import { Table, THead, Th, Td } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Dialog } from '../../components/ui/dialog';

const STATUSES = ['available', 'reserved', 'en_route', 'deployed', 'unavailable', 'maintenance'];

export default function ResourcesPage() {
  const [resources, setResources] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [zones, setZones] = useState<any[]>([]);
  const [status, setStatus] = useState('');
  const [type, setType] = useState('');
  const [agency, setAgency] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState<any>(null);
  const [form, setForm] = useState({ status: 'available', current_zone_id: '', eta_minutes: '' });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const r = await snapshotAPI.get();
    setResources(r.data.resources || []);
    setAllocations(r.data.allocations || []);
    setZones(r.data.zones || []);
  }, []);

  useEffect(() => {
    load().catch(() => setError('Could not load resource inventory.'));
    const t = setInterval(() => load().catch(() => null), 4000);
    return () => clearInterval(t);
  }, [load]);

  const filtered = useMemo(
    () => resources.filter((r) => (!status || r.status === status) && (!type || r.type === type) && (!agency || r.agency_id === agency)),
    [resources, status, type, agency]
  );

  const openEdit = (r: any) => {
    setEditing(r);
    setForm({
      status: r.status || 'available',
      current_zone_id: r.current_zone_id || '',
      eta_minutes: r.eta_minutes != null ? String(r.eta_minutes) : '',
    });
    setError(null);
  };

  const save = async () => {
    if (!editing) return;
    setBusy(true);
    setError(null);
    try {
      await resourcesAPI.patch(editing.id, {
        status: form.status,
        current_zone_id: form.current_zone_id || null,
        eta_minutes: form.eta_minutes === '' ? null : Number(form.eta_minutes),
        reason: 'Manual inventory correction',
      });
      setMessage(`${resourceCallsign(editing)} updated.`);
      setEditing(null);
      await load();
    } catch (e) {
      setError(apiError(e, 'The resource could not be updated.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader title="Resources" description="Digital twin of inventory. Edit status, assignment, and ETA. Changes are validated and audited by the backend." />
      {message && <div className="mb-4"><Notice>{message}</Notice></div>}
      {error && <div className="mb-4"><ErrorBanner message={error} /></div>}
      <div className="mb-4 flex flex-wrap gap-2">
        <Select aria-label="Filter by status" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s.replace('_', ' ').toUpperCase()}</option>
          ))}
        </Select>
        <Select aria-label="Filter by type" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option>
          {Array.from(new Set(resources.map((r) => r.type))).map((t) => (
            <option key={t as string} value={t as string}>{t as string}</option>
          ))}
        </Select>
        <Select aria-label="Filter by agency" value={agency} onChange={(e) => setAgency(e.target.value)}>
          <option value="">All agencies</option>
          {Array.from(new Set(resources.map((r) => r.agency_id))).map((t) => (
            <option key={t as string} value={t as string}>{t as string}</option>
          ))}
        </Select>
      </div>
      {filtered.length === 0 ? (
        <EmptyState title="No resources match these filters" hint="Load a scenario or clear filters." />
      ) : (
        <Table>
          <THead>
            <tr>
              <Th>Resource ID</Th>
              <Th>Agency</Th>
              <Th>Type</Th>
              <Th>Capability</Th>
              <Th>Status</Th>
              <Th>Location</Th>
              <Th>Assignment</Th>
              <Th>ETA</Th>
              <Th>Action</Th>
            </tr>
          </THead>
          <tbody>
            {filtered.map((r) => {
              const alloc = allocations.find((a) => a.resource_id === r.id);
              const assignment = alloc?.from_zone_id ? `${alloc.from_zone_id} → ${alloc.zone_id}` : (r.current_zone_id || '—');
              return (
                <tr key={r.id}>
                  <Td className="font-medium text-white">{resourceCallsign(r)}</Td>
                  <Td>{r.agency_id}</Td>
                  <Td>{r.type}</Td>
                  <Td>{Array.isArray(r.capabilities) ? r.capabilities.join(', ') : '—'}</Td>
                  <Td>
                    <Badge tone={r.status === 'en_route' ? 'warning' : r.status === 'available' ? 'success' : 'info'}>
                      {(r.status || '').replace('_', ' ')}
                    </Badge>
                  </Td>
                  <Td>{r.latitude && r.longitude ? `${Number(r.latitude).toFixed(3)}, ${Number(r.longitude).toFixed(3)}` : '—'}</Td>
                  <Td>{assignment}</Td>
                  <Td>{r.eta_minutes ? `${r.eta_minutes} min` : '—'}</Td>
                  <Td>
                    <Button variant="secondary" onClick={() => openEdit(r)}>Edit</Button>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}

      {editing && (
        <Dialog title="Edit Resource" onClose={() => !busy && setEditing(null)}>
          <p className="mb-3 text-sm font-medium text-white">{resourceCallsign(editing)}</p>
          <Label>
            Status
            <Select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              {STATUSES.map((s) => (
                <option key={s} value={s}>{s.replace('_', ' ').toUpperCase()}</option>
              ))}
            </Select>
          </Label>
          <Label className="mt-3">
            Assigned Zone
            <Select value={form.current_zone_id} onChange={(e) => setForm({ ...form, current_zone_id: e.target.value })}>
              <option value="">Unassigned</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>{z.name || z.id}</option>
              ))}
            </Select>
          </Label>
          <Label className="mt-3">
            ETA (minutes)
            <Input
              type="number"
              min={0}
              value={form.eta_minutes}
              onChange={(e) => setForm({ ...form, eta_minutes: e.target.value })}
              placeholder="Optional"
            />
          </Label>
          <div className="mt-4 flex gap-2">
            <Button variant="secondary" disabled={busy} onClick={() => setEditing(null)}>Cancel</Button>
            <Button disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save Changes'}</Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
