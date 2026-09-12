'use client';

import type { ReactNode } from 'react';
import { formatScore, resourceCallsign } from '../lib/ops';

export function AllocationDelta({
  delta,
  explanation,
  allocations,
}: {
  delta: any;
  explanation?: string;
  allocations?: any[];
}) {
  const moves = delta?.moves || [];
  const changes = (delta?.priority_changes || []).filter((p: any) => {
    if (p?.before == null || p?.after == null) return false;
    return Math.abs(Number(p.after) - Number(p.before)) >= 0.01;
  });
  const current = (allocations || []).filter((a) => a.status === 'approved' || a.status === 'pending');

  if (!delta && current.length === 0) {
    return <p className="text-sm text-muted">No allocation delta yet. Load a scenario, then inject an urgent report.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-6 md:grid-cols-2">
        <Column title="Before">
          {moves.length > 0
            ? moves.map((m: any, i: number) => (
                <div key={`b-${i}`} className="text-sm text-ink">
                  <span className="font-medium">{m.resource_id || m.name}</span>
                  {' → '}
                  {m.from_zone || 'unassigned'}
                </div>
              ))
            : current.length > 0
              ? current.map((a: any) => (
                  <div key={a.id} className="text-sm text-ink">
                    <span className="font-medium">{resourceCallsign({ id: a.resource_id })}</span>
                    {' → '}
                    {a.from_zone_id || a.zone_id}
                  </div>
                ))
              : <p className="text-sm text-muted">No previous assignments recorded for this delta.</p>}
        </Column>
        <Column title="After">
          {moves.length > 0
            ? moves.map((m: any, i: number) => (
                <div key={`a-${i}`} className="text-sm text-ink">
                  <span className="font-medium">{m.resource_id || m.name}</span>
                  {' → '}
                  {m.to_zone}
                </div>
              ))
            : current.length > 0
              ? current.map((a: any) => (
                  <div key={`after-${a.id}`} className="text-sm text-ink">
                    <span className="font-medium">{resourceCallsign({ id: a.resource_id })}</span>
                    {' → '}
                    {a.zone_id}
                  </div>
                ))
              : <p className="text-sm text-muted">No new assignments listed.</p>}
        </Column>
      </div>
      <div className="border-t border-line pt-3 text-sm">
        <div className="text-[13px] font-semibold text-ink">Reason</div>
        {changes.length === 0 ? (
          <p className="mt-1 text-muted">Resource movements respond to unmet demand and current zone priority.</p>
        ) : (
          changes.map((p: any) => (
            <p key={p.zone_id} className="mt-1 text-ink">
              {p.zone_id} priority {formatScore(p.before, 2)} → {formatScore(p.after, 2)}
            </p>
          ))
        )}
        {(explanation || delta?.summary) && <p className="mt-2 text-[13px] text-muted">{explanation || delta.summary}</p>}
      </div>
    </div>
  );
}

function Column({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-[13px] font-semibold text-muted">{title}</h3>
      {children}
    </div>
  );
}
