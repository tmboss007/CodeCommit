'use client';

import { eventAge, formatEventLabel, pipelineStatus, PIPELINE } from '../../lib/ops';
import { useOps } from '../../lib/ops-runtime';
import { EmptyState, ErrorBanner, PageHeader, Section } from '../../components/ui/chrome';
import { Table, THead, Th, Td } from '../../components/ui/table';

function lastEvent(events: any[], match: string) {
  return events.find((e) => `${e.agent || ''} ${e.event_type || ''} ${e.description || ''}`.toLowerCase().includes(match.toLowerCase()));
}

export default function AgentsPage() {
  const { data, error } = useOps();
  const events = data?.audit || [];

  return (
    <div className="space-y-8">
      <PageHeader title="Agents" />
      {error && <ErrorBanner message={error} />}
      <Table>
        <THead>
          <tr>
            <Th>Component</Th>
            <Th>Type</Th>
            <Th>Status</Th>
            <Th>Last event</Th>
            <Th>Duration</Th>
          </tr>
        </THead>
        <tbody>
          {PIPELINE.map((p) => {
            const status = pipelineStatus(events, p.match);
            const latest = lastEvent(events, p.match);
            return (
              <tr key={p.label}>
                <Td className="font-medium">{p.label}</Td>
                <Td>{p.kind}</Td>
                <Td className={status === 'FAILED' ? 'uppercase text-critical' : 'uppercase'}>{status}</Td>
                <Td>{latest ? formatEventLabel(latest.event_type) : '—'}</Td>
                <Td className="text-muted">{eventAge(latest?.timestamp)}</Td>
              </tr>
            );
          })}
        </tbody>
      </Table>
      <Section title="Event stream">
        {events.length === 0 && !error ? (
          <EmptyState title="No pipeline events yet" hint="Load a scenario or submit an incident." />
        ) : (
          <ul>
            {events.map((e: any) => (
              <li key={e.id} className="grid grid-cols-[5.5rem_1fr] gap-4 border-b border-line py-2 text-sm">
                <div className="tabular-nums text-muted">{e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour12: false }) : '—'}</div>
                <div>
                  <div className="font-semibold">{formatEventLabel(e.event_type)}</div>
                  <div className="text-muted">{e.agent || e.actor} · {e.description}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  );
}
