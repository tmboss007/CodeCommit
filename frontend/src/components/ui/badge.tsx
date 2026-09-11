import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

type Tone = 'neutral' | 'critical' | 'high' | 'elevated' | 'stable' | 'success' | 'warning' | 'info';

const tones: Record<Tone, string> = {
  neutral: 'border-slate-600 bg-slate-800 text-slate-200',
  critical: 'border-red-700 bg-red-950 text-red-200',
  high: 'border-orange-700 bg-orange-950 text-orange-200',
  elevated: 'border-amber-700 bg-amber-950 text-amber-200',
  stable: 'border-sky-700 bg-sky-950 text-sky-200',
  success: 'border-emerald-700 bg-emerald-950 text-emerald-200',
  warning: 'border-amber-700 bg-amber-950 text-amber-100',
  info: 'border-slate-500 bg-slate-800 text-slate-100',
};

export function Badge({
  tone = 'neutral',
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide', tones[tone], className)}>
      {children}
    </span>
  );
}
