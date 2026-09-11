'use client';

import { useEffect, useState } from 'react';
import { incidentsAPI, snapshotAPI } from '../../lib/api';
import { EmptyState, ErrorBanner } from '../../components/Status';
import { formatTimestamp } from '../../lib/utils';

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [zones, setZones] = useState<any[]>([]);
  const [needs, setNeeds] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [resources, setResources] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
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

  const submit = async (e: React.FormEvent) => {
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

  const incident = incidents.find((i) => i.id === selected) || incidents[0];
  const zone = zones.find((z) => z.id === incident?.zone_id);
  const incidentNeeds = needs.filter((n) => n.incident_id === incident?.id || n.zone_id === incident?.zone_id);
  const assigned = allocations.filter((a) => a.zone_id === incident?.zone_id);

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h1 className="mb-1 text-xl font-bold text-white">Incidents</h1>
        <p className="mb-3 text-sm text-slate-400">Submit a field report. The situation pipeline updates needs and response priority.</p>
        {error && <div className="mb-3"><ErrorBanner message={error} /></div>}
        <form onSubmit={submit} className="space-y-3">
          <label className="block text-sm text-slate-300">
            Zone
            <select value={zoneId} onChange={(e) => setZoneId(e.target.value)} className="mt-1 w-full rounded bg-slate-800 p-2 text-white">
              {(zones.length ? zones : [{ id: 'ZONE_A', name: 'Zone A' }]).map((z: any) => (
                <option key={z.id} value={z.id}>{z.name || z.id}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-slate-300">
            Source
            <input value={source} onChange={(e) => setSource(e.target.value)} className="mt-1 w-full rounded bg-slate-800 p-2 text-white" />
          </label>
          <label className="block text-sm text-slate-300">
            Description
            <textarea required value={report} onChange={(e) => setReport(e.target.value)} rows={5} className="mt-1 w-full rounded bg-slate-800 p-2 text-white" />
          </label>
          <button disabled={busy} className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">
            {busy ? 'Processing…' : 'Submit report'}
          </button>
        </form>
        {result && (
          <div className="mt-4 space-y-1 text-sm text-slate-300">
            <div>Created {result.incident_id}</div>
            <div>Type {result.situation_analysis?.incident_type} · confidence {result.situation_analysis?.confidence}</div>
            <div>Duplicate status: {result.duplicate_check?.duplicate_status}</div>
            <div>Response priority now {Number(result.zone_priority_updated || 0).toFixed(0)}</div>
            <div>{result.replanning_required ? `Replan required: ${result.replanning_reason}` : 'No replan required'}</div>
          </div>
        )}
      </section>
      <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <h2 className="mb-3 text-xl font-bold text-white">Open incidents</h2>
        {incidents.length === 0 ? (
          <EmptyState title="No incidents yet" hint="Submit a report or load a scenario." />
        ) : (
          <div className="space-y-3">
            {incidents.map((i) => (
              <button key={i.id} onClick={() => setSelected(i.id)} className={`w-full border-b border-slate-800 pb-3 text-left text-sm ${selected === i.id ? 'opacity-100' : 'opacity-80'}`}>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>{i.zone_id} · {i.incident_type || 'unclassified'} · {i.source}</span>
                  <span>{i.duplicate_status || 'NEW'}</span>
                </div>
                <p className="mt-1 text-slate-100">{i.report_text}</p>
              </button>
            ))}
          </div>
        )}
        {incident && (
          <div className="mt-4 rounded border border-slate-800 p-3 text-sm text-slate-300">
            <div className="font-medium text-white">Incident detail</div>
            <div>Source {incident.source} · {incident.timestamp ? formatTimestamp(incident.timestamp) : '—'}</div>
            <div>Location {zone ? `${zone.name} (${zone.latitude}, ${zone.longitude})` : incident.zone_id}</div>
            <div>Affected {incident.affected_population ?? 'unknown'} · confidence {incident.confidence ?? 'n/a'}</div>
            <div>Response priority {Number(zone?.priority_score || 0).toFixed(0)}</div>
            <div className="mt-2 text-xs uppercase text-slate-500">Needs</div>
            {incidentNeeds.length === 0 ? 'None recorded' : incidentNeeds.slice(0, 8).map((n) => (
              <div key={n.id}>{n.resource_type}: {n.quantity_required} {n.unit} required</div>
            ))}
            <div className="mt-2 text-xs uppercase text-slate-500">Assigned resources</div>
            {assigned.length === 0 ? 'None yet' : assigned.map((a) => {
              const r = resources.find((x) => x.id === a.resource_id);
              return <div key={a.id}>{r?.name || a.resource_id} → {a.zone_id} ({a.status})</div>;
            })}
          </div>
        )}
      </section>
    </div>
  );
}
