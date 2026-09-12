'use client';

import { useState } from 'react';
import { plansAPI } from '../lib/api';
import { apiError, formatScore } from '../lib/ops';
import { Button } from './ui/button';
import { Dialog } from './ui/dialog';
import { AllocationDelta } from './AllocationDelta';
import { ErrorBanner, Notice } from './ui/chrome';

export function RevisedPlanBanner({
  plan,
  delta,
  explanation,
  allocations,
  onChanged,
}: {
  plan: any;
  delta?: any;
  explanation?: string;
  allocations?: any[];
  onChanged?: () => Promise<void> | void;
}) {
  const [showReview, setShowReview] = useState(false);
  const [confirm, setConfirm] = useState<'approve' | 'reject' | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  if (!plan?.pending) return message ? <Notice>{message}</Notice> : null;

  const initial = plan.trigger === 'load_demo';
  const review = plan.review || {};
  const pri = (plan.priority_changes || [])[0];
  const zoneLabel = pri?.zone_id || pri?.zone || 'Priority';
  const movements = plan.resources_to_move ?? review.total_movements ?? 0;
  const agencies = plan.agencies_affected ?? 0;

  const run = async (kind: 'approve' | 'reject') => {
    setBusy(true);
    setError(null);
    try {
      if (kind === 'approve') await plansAPI.approve(plan.plan_id);
      else await plansAPI.reject(plan.plan_id);
      setMessage(kind === 'approve'
        ? 'Plan approved. Allocations, resources, and coordination tasks were updated.'
        : 'Plan rejected. Previous active plan was preserved.');
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
      <section className="border border-line bg-white">
        <div className="border-l-4 border-accent px-5 py-4">
          <div className="text-[15px] font-semibold text-ink">
            {initial ? 'Response plan ready' : 'Response plan updated'}
          </div>
          {pri && pri.before != null ? (
            <p className="mt-2 text-sm text-ink">
              {zoneLabel}: {formatScore(pri.before, 2)} → {formatScore(pri.after, 2)}
            </p>
          ) : (
            <p className="mt-2 text-sm text-muted">Initial allocation awaiting approval.</p>
          )}
          <p className="mt-1 text-sm text-muted">
            {movements} resource movements · {agencies} agencies affected
          </p>
          {plan.estimated_impact && <p className="mt-2 text-sm text-ink">{plan.estimated_impact}</p>}
          <p className="mt-1 text-[12px] text-muted">Plan {plan.plan_id}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={() => setConfirm('approve')}>{initial ? 'Approve plan' : 'Approve revised plan'}</Button>
            <Button variant="outline" onClick={() => setShowReview(true)}>Review changes</Button>
            <Button variant="danger" onClick={() => setConfirm('reject')}>Reject</Button>
          </div>
        </div>
      </section>

      {showReview && (
        <Dialog title="Review changes" wide onClose={() => setShowReview(false)}>
          <AllocationDelta delta={delta || plan.delta} explanation={explanation} allocations={allocations} />
          {(review.before?.length || review.after?.length) ? (
            <div className="mt-4 grid gap-4 text-sm md:grid-cols-2">
              <div>
                <div className="mb-2 text-[13px] font-semibold text-muted">Assignment before</div>
                {(review.before || []).map((line: string, i: number) => <div key={i}>{line}</div>)}
              </div>
              <div>
                <div className="mb-2 text-[13px] font-semibold text-muted">Assignment after</div>
                {(review.after || []).map((line: string, i: number) => <div key={i}>{line}</div>)}
              </div>
            </div>
          ) : null}
          <div className="mt-4 flex gap-2">
            <Button variant="outline" onClick={() => setShowReview(false)}>Close</Button>
            <Button onClick={() => { setShowReview(false); setConfirm('approve'); }}>Approve plan</Button>
          </div>
        </Dialog>
      )}

      {confirm && (
        <Dialog title={confirm === 'approve' ? 'Approve this plan?' : 'Reject this plan?'} onClose={() => !busy && setConfirm(null)}>
          <p className="text-sm text-muted">
            {confirm === 'approve'
              ? 'All pending tasks in this plan will be validated and applied together. If validation fails, nothing will change.'
              : 'New allocations will not be deployed. The previous active plan stays in effect.'}
          </p>
          {busy && <p className="mt-3 text-sm text-muted">Applying plan…</p>}
          <div className="mt-4 flex gap-2">
            <Button disabled={busy} onClick={() => run(confirm)}>{busy ? 'Working…' : 'Confirm'}</Button>
            <Button variant="outline" disabled={busy} onClick={() => setConfirm(null)}>Cancel</Button>
          </div>
        </Dialog>
      )}
    </>
  );
}
