'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { coordinationAPI, snapshotAPI } from '../../lib/api';
import { apiError } from '../../lib/ops';
import { RevisedPlanBanner } from '../../components/RevisedPlanBanner';
import { EmptyState, ErrorBanner, Notice, PageHeader } from '../../components/ui/chrome';
import { Button } from '../../components/ui/button';
import { Card, CardBody } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { cn } from '../../lib/utils';

const TABS = [
  { id: 'pending', label: 'Pending Approval' },
  { id: 'active', label: 'Active' },
  { id: 'history', label: 'History' },
  { id: 'rejected', label: 'Rejected' },
] as const;

export default function CoordinationPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [allocations, setAllocations] = useState<any[]>([]);
  const [snap, setSnap] = useState<any>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]['id']>('pending');

  const load = useCallback(async () => {
    const res = await snapshotAPI.get();
    setSnap(res.data);
    setTasks(res.data.tasks || []);
    setAllocations(res.data.allocations || []);
  }, []);

  useEffect(() => {
    load().catch(() => setError('Could not load coordination tasks.'));
    const t = setInterval(() => load().catch(() => null), 4000);
    return () => clearInterval(t);
  }, [load]);

  const act = async (id: string, kind: 'approve' | 'reject') => {
    try {
      if (kind === 'approve') await coordinationAPI.approveTask(id);
      else await coordinationAPI.rejectTask(id);
      setMessage(kind === 'approve' ? 'Approved — allocation and resource state updated.' : 'Rejected — allocation was not applied.');
      setError(null);
      await load();
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
      history: tasks.filter((t) => t.status === 'superseded' || t.status === 'completed' || ((t.status === 'approved' || t.status === 'in_progress') && planOf(t) && planOf(t) !== activePlanId)),
      rejected: tasks.filter((t) => t.status === 'rejected'),
    };
  }, [tasks, allocations, activePlanId]);

  const pendingPlan = snap?.revised_plan?.pending;
  const items = grouped[tab];

  return (
    <div className="space-y-5">
      <PageHeader
        title="Coordination"
        description="Approve a complete response plan in one action. The Active tab shows only the current operational plan."
        actions={activePlanId ? <div className="text-xs text-slate-500">Current active plan {activePlanId}</div> : null}
      />
      {message && <Notice>{message}</Notice>}
      {error && <ErrorBanner message={error} />}

      <RevisedPlanBanner
        plan={snap?.revised_plan}
        delta={snap?.delta}
        explanation={snap?.explanation}
        onChanged={load}
      />

      {tasks.length === 0 && <EmptyState title="No agency tasks" hint="Load a scenario to generate an allocation plan." />}

      {pendingPlan && (
        <Button variant="ghost" className="px-0" onClick={() => setShowDetails((v) => !v)}>
          {showDetails ? 'Hide individual task decisions' : 'Review Details — approve or reject individual cards'}
        </Button>
      )}

      {(!pendingPlan || showDetails) && tasks.length > 0 && (
        <div>
          <div role="tablist" aria-label="Task status" className="mb-3 flex flex-wrap gap-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm',
                  tab === t.id ? 'bg-slate-100 text-slate-950' : 'text-slate-300 hover:bg-slate-800',
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
              items.map((t) => {
                const alloc = allocations.find((a) => a.id === t.allocation_id);
                return (
                  <Card key={t.id} className="mb-3">
                    <CardBody>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-sky-300">{t.agency_id}</span>
                        <Badge>{t.status}</Badge>
                        {t.plan_id && <Badge tone={t.plan_id === activePlanId ? 'success' : 'neutral'}>{t.plan_id}</Badge>}
                      </div>
                      <p className="mt-1 text-sm text-white">{t.action}</p>
                      {alloc && (
                        <p className="mt-2 text-xs text-slate-400">
                          {alloc.from_zone_id ? `${alloc.from_zone_id} → ` : ''}
                          {alloc.zone_id} · {alloc.reason}
                        </p>
                      )}
                      {t.status === 'pending' && (
                        <div className="mt-3 flex gap-2">
                          <Button variant="success" onClick={() => act(t.id, 'approve')}>Approve task</Button>
                          <Button variant="danger" onClick={() => act(t.id, 'reject')}>Reject task</Button>
                        </div>
                      )}
                    </CardBody>
                  </Card>
                );
              })
            )}
          </div>
        </div>
      )}

      {pendingPlan && !showDetails && grouped.pending.length > 0 && (
        <p className="text-sm text-slate-400">{grouped.pending.length} pending tasks included in the plan above.</p>
      )}
    </div>
  );
}
