'use client';

import { useState } from 'react';
import { plansAPI } from '../lib/api';
import { apiError, formatScore } from '../lib/ops';
import { Button } from './ui/button';
import { Card, CardBody } from './ui/card';
import { Dialog } from './ui/dialog';
import { AllocationDelta } from './AllocationDelta';
import { ErrorBanner, Notice } from './ui/chrome';

export function RevisedPlanBanner({
  plan,
  delta,
  explanation,
  onChanged,
}: {
  plan: any;
  delta?: any;
  explanation?: string;
  onChanged?: () => Promise<void> | void;
}) {
  const [showReview, setShowReview] = useState(false);
  const [confirm, setConfirm] = useState<'approve' | 'reject' | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (!plan?.pending) return message ? <Notice>{message}</Notice> : null;

  const title = plan.trigger === 'load_demo' ? 'RESPONSE PLAN' : 'REVISED RESPONSE PLAN';
  const review = plan.review || {};
  const pri = (plan.priority_changes || [])[0];

  const run = async (kind: 'approve' | 'reject') => {
    setBusy(true);
    setError(null);
    try {
      if (kind === 'approve') await plansAPI.approve(plan.plan_id);
      else await plansAPI.reject(plan.plan_id);
      setMessage(kind === 'approve'
        ? 'Revised plan approved. Allocations, resources, and coordination tasks were updated.'
        : 'Revised plan rejected. Previous active plan was preserved.');
      setConfirm(null);
      setShowReview(false);
      await onChanged?.();
    } catch (e) {
      setError(apiError(e, 'The plan decision could not be saved.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {message && <Notice>{message}</Notice>}
      {error && <ErrorBanner message={error} />}
      <Card className="border-amber-700/80 bg-slate-900">
        <CardBody className="space-y-4">
          <div className="text-[11px] font-semibold tracking-[0.2em] text-amber-400">{title}</div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Fact label="Priority" value={pri ? `${formatScore(pri.before, 2)} → ${formatScore(pri.after, 2)}` : 'No score change captured'} />
            <Fact label="Movements" value={`${plan.resources_to_move ?? review.total_movements ?? 0} resource movements`} />
            <Fact label="Agencies" value={`${plan.agencies_affected ?? 0} agencies affected`} />
            <Fact label="Plan ID" value={plan.plan_id} />
          </div>
          <p className="text-sm text-slate-300">{plan.estimated_impact || 'Pending allocations will be deployed if approved.'}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setShowReview(true)}>Review Changes</Button>
            <Button variant="success" onClick={() => setConfirm('approve')}>Approve Revised Plan</Button>
            <Button variant="danger" onClick={() => setConfirm('reject')}>Reject Revised Plan</Button>
          </div>
        </CardBody>
      </Card>

      {showReview && (
        <Dialog title="Review Changes" wide onClose={() => setShowReview(false)}>
          <AllocationDelta delta={delta || plan.delta} explanation={explanation} />
          {(review.before?.length || review.after?.length) ? (
            <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm">
              <div>
                <div className="mb-2 text-[11px] uppercase tracking-wide text-slate-500">Assignment before</div>
                {(review.before || []).map((line: string, i: number) => <div key={i} className="text-slate-300">{line}</div>)}
              </div>
              <div>
                <div className="mb-2 text-[11px] uppercase tracking-wide text-slate-500">Assignment after</div>
                {(review.after || []).map((line: string, i: number) => <div key={i} className="text-emerald-300">{line}</div>)}
              </div>
            </div>
          ) : null}
          <div className="mt-4 flex gap-2">
            <Button variant="secondary" onClick={() => setShowReview(false)}>Close</Button>
            <Button variant="success" onClick={() => { setShowReview(false); setConfirm('approve'); }}>Approve Revised Plan</Button>
          </div>
        </Dialog>
      )}

      {confirm && (
        <Dialog title={confirm === 'approve' ? 'Approve this plan?' : 'Reject this plan?'} onClose={() => !busy && setConfirm(null)}>
          <p className="text-sm text-slate-400">
            {confirm === 'approve'
              ? 'All pending tasks in this plan will be validated and applied together. If validation fails, nothing will change.'
              : 'New allocations will not be deployed. The previous active plan stays in effect.'}
          </p>
          {busy && <p className="mt-3 text-sm text-amber-300">Applying plan…</p>}
          <div className="mt-4 flex gap-2">
            <Button disabled={busy} onClick={() => run(confirm)}>{busy ? 'Working…' : 'Confirm'}</Button>
            <Button variant="secondary" disabled={busy} onClick={() => setConfirm(null)}>Cancel</Button>
          </div>
        </Dialog>
      )}
    </>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">{label}</div>
      <div className="text-sm font-medium text-white">{value}</div>
    </div>
  );
}
