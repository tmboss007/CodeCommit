'use client';

export function AllocationDelta({ delta }: { delta: any }) {
  if (!delta) {
    return <div className="text-sm text-slate-400">No allocation delta yet. Load a scenario, then inject an urgent report.</div>;
  }

  const before = delta.before_by_zone || {};
  const after = delta.after_by_zone || {};
  const zones = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-300">BEFORE</h3>
          {zones.map((z) => (
            <div key={`b-${z}`} className="mb-1 text-sm">
              <span className="font-medium text-white">{z}:</span>{' '}
              {formatCounts(before[z])}
            </div>
          ))}
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-300">AFTER</h3>
          {zones.map((z) => (
            <div key={`a-${z}`} className="mb-1 text-sm">
              <span className="font-medium text-white">{z}:</span>{' '}
              {formatCounts(after[z])}
            </div>
          ))}
        </div>
      </div>
      {delta.moves?.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-amber-300">CHANGE</h3>
          {delta.moves.map((m: any, i: number) => (
            <div key={i} className="rounded border border-amber-700/50 bg-amber-950/40 p-2 text-sm">
              <div className="font-medium text-amber-100">{m.name || m.resource_id}</div>
              <div className="text-slate-300">
                {m.from_zone} → {m.to_zone}
              </div>
              {m.reason && <div className="mt-1 text-xs text-slate-400">{m.reason}</div>}
            </div>
          ))}
        </div>
      )}
      <div className="text-xs text-slate-500">{delta.summary}</div>
    </div>
  );
}

function formatCounts(counts?: Record<string, number>) {
  if (!counts || !Object.keys(counts).length) return <span className="text-slate-500">none</span>;
  return Object.entries(counts)
    .map(([k, v]) => `${v} ${k.replace('_', ' ')}`)
    .join(', ');
}
