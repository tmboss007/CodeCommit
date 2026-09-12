'use client';

import { useMemo, useState } from 'react';
import { coordinationAPI } from '../../lib/api';
import { apiError } from '../../lib/ops';
import { useOps } from '../../lib/ops-runtime';
import { RevisedPlanBanner } from '../../components/RevisedPlanBanner';
import { EmptyState, ErrorBanner, Notice, PageHeader, Section } from '../../components/ui/chrome';
import { Button } from '../../components/ui/button';
import { cn } from '../../lib/utils';

const TABS = [
  { id: 'pending', label: 'Pending approval' },
  { id: 'active', label: 'Active' },
  { id: 'completed', label: 'Completed' },
  { id: 'history', label: 'History' },
  { id: 'rejected', label: 'Rejected' },
] as const;

export default function CoordinationPage() {
  const { data: snap, error: opsError, refresh } = useOps();
  const tasks: any[] = snap?.tasks || [];
  const allocations: any[] = snap?.allocations || [];
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]['id']>('pending');

  const act = async (id: string, kind: 'approve' | 'reject') => {
    try {
      if (kind === 'approve') await coordinationAPI.approveTask(id);
      else await coordinationAPI.rejectTask(id);
      setMessage(kind === 'approve' ? 'Approved — allocation and resource state updated.' : 'Rejected — allocation was not applied.');
      setError(null);
      await refresh(true);
    } catch (e) {
      setError(apiError(e, 'The decision could not be saved. Refresh and try again.'));
    }
  };

  const activePlanId = snap?.active_plan_id;
  const grouped = useMemo(() => {
    const planOf = (t: any) => t.plan_id || allocations.find((a) => a.id === t.allocation_id)?.plan_id;
    return {
      pending: tasks.filter((t) => t.status === 'pending'),
      active: tasks.filter((t) => (t.status === 'approved' || t.status === 'in_progress') && planOf(t) === activePlanId),
      completed: tasks.filter((t) => t.status === 'completed'),
      history: tasks.filter((t) => t.status === 'superseded' || ((t.status === 'approved' || t.status === 'in_progress') && planOf(t) && planOf(t) !== activePlanId)),
      rejected: tasks.filter((t) => t.status === 'rejected'),
    };
  }, [tasks, allocations, activePlanId]);

  const pendingPlan = snap?.revised_plan?.pending;
  const items = grouped[tab];

  return (
    <div className="space-y-8">
      <PageHeader title="Coordination" />
      {message && <Notice>{message}</Notice>}
      {(error || opsError) && <ErrorBanner message={error || opsError || ''} />}

      <Section title="Current active plan">
        {activePlanId ? (
          <p className="text-sm text-ink">{activePlanId}</p>
        ) : (
          <p className="text-sm text-muted">No active plan. Load a scenario and approve the initial allocation.</p>
        )}
      </Section>

      <RevisedPlanBanner
        plan={snap?.revised_plan}
        delta={snap?.delta}
        explanation={snap?.explanation}
        allocations={allocations}
        onChanged={refresh}
      />

      {tasks.length === 0 && <EmptyState title="No agency tasks" hint="Load a scenario to generate an allocation plan." />}

      {pendingPlan && (
        <Button variant="ghost" className="px-0" onClick={() => setShowDetails((v) => !v)}>
          {showDetails ? 'Hide individual task decisions' : 'Review details — approve or reject individual tasks'}
        </Button>
      )}

      {(!pendingPlan || showDetails) && tasks.length > 0 && (
        <div>
          <div role="tablist" aria-label="Task status" className="mb-3 flex flex-wrap gap-4 border-b border-line">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  '-mb-px border-b-2 px-0 py-2 text-sm',
                  tab === t.id ? 'border-brand font-semibold text-ink' : 'border-transparent text-muted',
                )}
              >
                {t.label} ({grouped[t.id].length})
              </button>
            ))}
          </div>
          <div role="tabpanel">
            {items.length === 0 ? (
              <EmptyState title={`No ${tab} tasks`} />
            ) : (
              <ul>
                {items.map((t) => {
                  const alloc = allocations.find((a) => a.id === t.allocation_id);
                  return (
                    <li key={t.id} className="border-b border-line py-3">
                      <div className="flex flex-wrap items-baseline gap-3 text-sm">
                        <span className="font-medium text-ink">{t.agency_id}</span>
                        <span className="uppercase text-muted">{t.status}</span>
                        {t.plan_id && <span className="text-[12px] text-muted">{t.plan_id}</span>}
                      </div>
                      <p className="mt-1 text-sm text-ink">{t.action}</p>
                      {alloc && (
                        <p className="mt-1 text-[13px] text-muted">
                          {alloc.from_zone_id ? `${alloc.from_zone_id} → ` : ''}
                          {alloc.zone_id} · {alloc.reason}
                        </p>
                      )}
                      {t.status === 'pending' && (
                        <div className="mt-2 flex gap-2">
                          <Button onClick={() => act(t.id, 'approve')}>Approve task</Button>
                          <Button variant="danger" onClick={() => act(t.id, 'reject')}>Reject task</Button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}

      {pendingPlan && !showDetails && grouped.pending.length > 0 && (
        <p className="text-sm text-muted">{grouped.pending.length} pending tasks included in the plan above.</p>
      )}
    </div>
  );
}
