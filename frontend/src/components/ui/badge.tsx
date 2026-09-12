import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

type Tone = 'neutral' | 'critical' | 'high' | 'elevated' | 'stable' | 'success' | 'warning' | 'info';

const tones: Record<Tone, string> = {
  neutral: 'bg-[#eef1f4] text-neutral',
  critical: 'bg-[#fbe9e7] text-critical',
  high: 'bg-[#fff0e4] text-high',
  elevated: 'bg-[#fff4df] text-warning',
  stable: 'bg-[#eef1f4] text-muted',
  success: 'bg-[#e6f4ed] text-success',
  warning: 'bg-[#fff4df] text-warning',
  info: 'bg-[#edf2f7] text-muted',
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
    <span className={cn('inline-flex items-center rounded-[3px] px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-[0.05em]', tones[tone], className)}>
      {children}
    </span>
  );
}
