'use client';

import { useMemo, useState, type FormEvent } from 'react';
import { incidentsAPI } from '../../lib/api';
import { formatTimestamp } from '../../lib/utils';
import { formatScore, severityTier } from '../../lib/ops';
import { useOps } from '../../lib/ops-runtime';
import { EmptyState, ErrorBanner, PageHeader, Section } from '../../components/ui/chrome';
import { Button } from '../../components/ui/button';
import { Input, Label, Select, Textarea } from '../../components/ui/input';
import { Table, THead, Th, Td } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';

export default function IncidentsPage() {
  const { data, error: opsError, refresh } = useOps();
  const incidents: any[] = data?.incidents || [];
  const zones: any[] = data?.zones || [];
  const needs: any[] = data?.needs || [];
  const allocations: any[] = data?.allocations || [];
  const resources: any[] = data?.resources || [];
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [report, setReport] = useState('');
  const [zoneId, setZoneId] = useState('ZONE_A');
  const [source, setSource] = useState('operator');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

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
      await refresh(true);
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
  const tier = severityTier(zone?.priority_score);

  return (
    <div className="space-y-8">
      <PageHeader title="Incidents" />
      {error && <ErrorBanner message={error} />}
      {opsError && !error && <ErrorBanner message={opsError} />}

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
              <Th>Priority</Th>
              <Th>Incident</Th>
              <Th>Zone</Th>
              <Th>Severity</Th>
              <Th>Affected</Th>
              <Th>Confidence</Th>
              <Th>Status</Th>
            </tr>
          </THead>
          <tbody>
            {filtered.map((i) => {
              const z = zones.find((zz) => zz.id === i.zone_id);
              const st = severityTier(z?.priority_score);
              return (
                <tr
                  key={i.id}
                  tabIndex={0}
                  role="button"
                  aria-pressed={selected === i.id}
                  className={`cursor-pointer ${selected === i.id ? 'bg-surface2' : 'hover:bg-surface2'}`}
                  onClick={() => setSelected(i.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelected(i.id);
                    }
                  }}
                >
                  <Td><Badge tone={st.tone}>{st.label}</Badge></Td>
                  <Td className="font-medium">{i.incident_type || 'unclassified'}</Td>
                  <Td>{i.zone_id}</Td>
                  <Td>{formatScore(z?.severity ?? i.analysis_result?.severity, 1)}</Td>
                  <Td>{i.affected_population ?? '—'}</Td>
                  <Td>{i.confidence ?? '—'}</Td>
                  <Td>{i.status}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}

      <div className="grid gap-8 lg:grid-cols-12">
        <Section title="Incident detail" className="lg:col-span-7">
          {!incident ? (
            <EmptyState title="Select an incident" />
          ) : (
            <div className="space-y-2 border-t border-line pt-3 text-sm">
              <p>{incident.report_text}</p>
              <p className="text-muted">Source {incident.source} · {incident.timestamp ? formatTimestamp(incident.timestamp) : '—'}</p>
              <p className="text-muted">Location {zone ? zone.name : incident.zone_id} · {incident.id}</p>
              <p className="text-muted">
                Priority <Badge tone={tier.tone}>{tier.label}</Badge> {formatScore(zone?.priority_score, 2)} · severity {formatScore(zone?.severity, 1)} / 10
              </p>
            </div>
          )}
          <form onSubmit={submit} className="mt-6 space-y-3 border-t border-line pt-4">
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
            <p className="mt-3 text-[13px] text-muted">
              Created {result.incident_id}. Duplicate {result.duplicate_check?.duplicate_status}. Priority {formatScore(result.zone_priority_updated)}.
              {result.replanning_required ? ` Replan: ${result.replanning_reason}` : ' No replan required.'}
            </p>
          )}
        </Section>
        <Section title="Needs and assignments" className="lg:col-span-5">
          <div className="border-t border-line pt-3 text-sm">
            <div className="mb-2 font-medium">Needs</div>
            {incidentNeeds.length === 0 ? <p className="text-muted">None recorded</p> : incidentNeeds.slice(0, 10).map((n) => (
              <div key={n.id} className="border-b border-line py-1.5">{n.resource_type}: {n.quantity_required} {n.unit} required · remaining {n.quantity_remaining ?? '—'}</div>
            ))}
            <div className="mb-2 mt-4 font-medium">Assigned resources</div>
            {assigned.length === 0 ? <p className="text-muted">None yet</p> : assigned.map((a) => {
              const r = resources.find((x) => x.id === a.resource_id);
              return <div key={a.id} className="border-b border-line py-1.5">{r?.name || a.resource_id} → {a.zone_id} ({a.status})</div>;
            })}
          </div>
        </Section>
      </div>
    </div>
  );
}
