'use client';

import type { ReactNode } from 'react';
import { formatScore } from '../lib/ops';

export function AllocationDelta({ delta, explanation }: { delta: any; explanation?: string }) {
  if (!delta) {
    return <p className="text-sm text-slate-400">No allocation delta yet. Load a scenario, then inject an urgent report.</p>;
  }

  const moves = delta.moves || [];
  const changes = (delta.priority_changes || []).filter((p: any) => {
    if (p?.before == null || p?.after == null) return false;
    return Math.abs(Number(p.after) - Number(p.before)) >= 0.01;
  });

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Column title="Before">
          {moves.length === 0 && <p className="text-sm text-slate-500">No prior assignment listed</p>}
          {moves.map((m: any, i: number) => (
            <div key={`b-${i}`} className="text-sm text-slate-300">
              <span className="font-medium text-white">{m.resource_id || m.name}</span>
              {' → '}
              {m.from_zone || 'unassigned'}
            </div>
          ))}
        </Column>
        <Column title="After">
          {moves.length === 0 && <p className="text-sm text-slate-500">No new assignment listed</p>}
          {moves.map((m: any, i: number) => (
            <div key={`a-${i}`} className="text-sm text-emerald-300">
              <span className="font-medium text-white">{m.resource_id || m.name}</span>
              {' → '}
              {m.to_zone}
            </div>
          ))}
        </Column>
      </div>
      <div className="rounded-md border border-slate-800 bg-slate-950/60 p-3 text-sm">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Why</div>
        {changes.length === 0 ? (
          <p className="mt-1 text-slate-300">Resource movements respond to unmet demand and current zone priority. No additional priority score change was recorded for this replan.</p>
        ) : (
          changes.map((p: any) => (
            <p key={p.zone_id} className="mt-1 text-slate-200">
              {p.zone_id} priority increased: {formatScore(p.before, 2)} → {formatScore(p.after, 2)}
            </p>
          ))
        )}
        <p className="mt-2 text-slate-400">Expected effect: higher critical-demand coverage where resources are moved.</p>
        {(explanation || delta.summary) && <p className="mt-2 text-xs text-slate-500">{explanation || delta.summary}</p>}
      </div>
    </div>
  );
}

function Column({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">{title}</h3>
      {children}
    </div>
  );
}
