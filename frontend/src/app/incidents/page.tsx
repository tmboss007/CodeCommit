'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { incidentsAPI, snapshotAPI } from '../../lib/api';
import { formatTimestamp } from '../../lib/utils';
import { formatScore } from '../../lib/ops';
import { EmptyState, ErrorBanner, PageHeader } from '../../components/ui/chrome';
import { Button } from '../../components/ui/button';
import { Card, CardBody, CardHeader, CardTitle } from '../../components/ui/card';
import { Input, Label, Select, Textarea } from '../../components/ui/input';
import { Table, THead, Th, Td } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [zones, setZones] = useState<any[]>([]);
  const [needs, setNeeds] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [resources, setResources] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [report, setReport] = useState('');
  const [zoneId, setZoneId] = useState('ZONE_A');
  const [source, setSource] = useState('operator');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const snap = await snapshotAPI.get();
    setIncidents(snap.data.incidents || []);
    setZones(snap.data.zones || []);
    setNeeds(snap.data.needs || []);
    setAllocations(snap.data.allocations || []);
    setResources(snap.data.resources || []);
  };

  useEffect(() => {
    load().catch(() => setError('Could not load incidents. Confirm the API is available.'));
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (report.trim().length < 12) {
      setError('Describe the incident in more detail before submitting.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await incidentsAPI.create({ report_text: report.trim(), source, zone_id: zoneId });
      setResult(res.data);
      setSelected(res.data.incident_id);
      setReport('');
      await load();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Incident could not be processed. Try again.');
    } finally {
      setBusy(false);
    }
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return incidents;
    return incidents.filter((i) => `${i.id} ${i.zone_id} ${i.source} ${i.incident_type} ${i.report_text} ${i.duplicate_status}`.toLowerCase().includes(q));
  }, [incidents, query]);

  const incident = incidents.find((i) => i.id === selected) || incidents[0];
  const zone = zones.find((z) => z.id === incident?.zone_id);
  const incidentNeeds = needs.filter((n) => n.incident_id === incident?.id || n.zone_id === incident?.zone_id);
  const assigned = allocations.filter((a) => a.zone_id === incident?.zone_id);

  return (
    <div className="space-y-5">
      <PageHeader title="Incidents" description="Search field reports and inspect needs, priority, and assigned resources." />
      {error && <ErrorBanner message={error} />}

      <Label>
        Search incidents
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Zone, source, type, text…" />
      </Label>

      {filtered.length === 0 ? (
        <EmptyState title="No incidents yet" hint="Submit a report or load a scenario." />
      ) : (
        <Table>
          <THead>
            <tr>
              <Th>Time</Th>
              <Th>Location</Th>
              <Th>Type</Th>
              <Th>Source</Th>
              <Th>Affected</Th>
              <Th>Confidence</Th>
              <Th>Duplicate</Th>
            </tr>
          </THead>
          <tbody>
            {filtered.map((i) => (
              <tr
                key={i.id}
                className={`cursor-pointer ${selected === i.id ? 'bg-slate-800/70' : 'hover:bg-slate-900'}`}
                onClick={() => setSelected(i.id)}
              >
                <Td>{i.timestamp ? formatTimestamp(i.timestamp) : '—'}</Td>
                <Td>{i.zone_id}</Td>
                <Td>
                  <Badge tone="info">{i.incident_type || 'unclassified'}</Badge>
                </Td>
                <Td><Badge>{i.source}</Badge></Td>
                <Td>{i.affected_population ?? '—'}</Td>
                <Td>{i.confidence ?? '—'}</Td>
                <Td><Badge tone={i.duplicate_status === 'NEW' ? 'success' : 'warning'}>{i.duplicate_status || 'NEW'}</Badge></Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Incident information</CardTitle></CardHeader>
          <CardBody className="space-y-2 text-sm text-slate-300">
            {!incident ? (
              <EmptyState title="Select an incident" />
            ) : (
              <>
                <p className="text-white">{incident.report_text}</p>
                <p>Source {incident.source} · {incident.timestamp ? formatTimestamp(incident.timestamp) : '—'}</p>
                <p>Location {zone ? `${zone.name}` : incident.zone_id}</p>
                <p>Affected {incident.affected_population ?? 'unknown'} · confidence {incident.confidence ?? 'n/a'}</p>
                <p>Status {incident.status} · {incident.id}</p>
              </>
            )}
            <form onSubmit={submit} className="space-y-3 border-t border-slate-800 pt-4">
              <Label>
                Zone
                <Select value={zoneId} onChange={(e) => setZoneId(e.target.value)}>
                  {(zones.length ? zones : [{ id: 'ZONE_A', name: 'Zone A' }]).map((z: any) => (
                    <option key={z.id} value={z.id}>{z.name || z.id}</option>
                  ))}
                </Select>
              </Label>
              <Label>
                Source
                <Input value={source} onChange={(e) => setSource(e.target.value)} />
              </Label>
              <Label>
                Description
                <Textarea required value={report} onChange={(e) => setReport(e.target.value)} rows={4} />
              </Label>
              <Button disabled={busy}>{busy ? 'Processing…' : 'Submit report'}</Button>
            </form>
            {result && (
              <div className="text-xs text-slate-400">
                Created {result.incident_id}. Duplicate {result.duplicate_check?.duplicate_status}. Priority {formatScore(result.zone_priority_updated)}.
                {result.replanning_required ? ` Replan: ${result.replanning_reason}` : ' No replan required.'}
              </div>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader><CardTitle>Needs / priority / allocation</CardTitle></CardHeader>
          <CardBody className="space-y-3 text-sm text-slate-300">
            <p>Response priority {formatScore(zone?.priority_score)} / 100 · severity {formatScore(zone?.severity, 1)} / 10</p>
            <div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Needs</div>
              {incidentNeeds.length === 0 ? 'None recorded' : incidentNeeds.slice(0, 10).map((n) => (
                <div key={n.id}>{n.resource_type}: {n.quantity_required} {n.unit} required · remaining {n.quantity_remaining ?? '—'}</div>
              ))}
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500">Assigned resources</div>
              {assigned.length === 0 ? 'None yet' : assigned.map((a) => {
                const r = resources.find((x) => x.id === a.resource_id);
                return <div key={a.id}>{r?.name || a.resource_id} → {a.zone_id} ({a.status})</div>;
              })}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
