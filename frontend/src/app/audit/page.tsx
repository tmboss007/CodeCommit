'use client';

import { useState } from 'react';
import { eventKind, formatEventLabel } from '../../lib/ops';
import { useOps } from '../../lib/ops-runtime';
import { EmptyState, ErrorBanner, PageHeader } from '../../components/ui/chrome';
import { cn } from '../../lib/utils';

const kindClass: Record<string, string> = {
  approved: 'text-success',
  replan: 'text-brand',
  resource: 'text-ink',
  priority: 'text-high',
  default: 'text-ink',
};

export default function AuditPage() {
  const { data, error } = useOps();
  const events = data?.audit || [];
  const [open, setOpen] = useState<string | null>(null);

  return (
    <div>
      <PageHeader title="Audit" />
      {error && <ErrorBanner message={error} />}
      {events.length === 0 && !error ? (
        <EmptyState title="Audit log is empty" hint="Operational actions will appear here." />
      ) : (
        <ol>
          {events.map((e: any) => {
            const expanded = open === e.id;
            const kind = eventKind(e.event_type);
            return (
              <li key={e.id} className="border-b border-line">
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setOpen(expanded ? null : e.id)}
                  className="w-full py-3 text-left"
                >
                  <div className="flex flex-wrap items-baseline gap-3 text-[13px] text-muted">
                    <span className="tabular-nums">{e.timestamp ? new Date(e.timestamp).toLocaleString() : '—'}</span>
                    <span className={cn('font-semibold', kindClass[kind])}>{formatEventLabel(e.event_type)}</span>
                    <span>{e.agent || e.actor}</span>
                  </div>
                  <p className="mt-1 text-sm text-ink">{e.description}</p>
                </button>
                {expanded && (
                  <div className="mb-3 grid gap-3 bg-surface2 p-3 text-[12px] text-muted md:grid-cols-2">
                    <pre className="overflow-auto whitespace-pre-wrap">Previous state{'\n'}{JSON.stringify(e.previous_state ?? null, null, 2)}</pre>
                    <pre className="overflow-auto whitespace-pre-wrap">New state{'\n'}{JSON.stringify(e.new_state ?? null, null, 2)}</pre>
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
