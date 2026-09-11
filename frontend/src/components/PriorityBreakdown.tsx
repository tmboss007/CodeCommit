import { formatScore, severityTier } from '../lib/ops';
import { Badge } from './ui/badge';

export function PriorityBreakdown({ score, breakdown }: { score: number; breakdown?: Record<string, number> | null }) {
  const tier = severityTier(score);
  return (
    <div className="text-right">
      <div className="flex items-center justify-end gap-2">
        <Badge tone={tier.tone}>{tier.label}</Badge>
        <span className="text-xl font-semibold tabular-nums text-white">{formatScore(score)} / 100</span>
      </div>
      {breakdown && (
        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-slate-400">
          <span>Severity {breakdown.severity}</span>
          <span>Population {breakdown.affected_population}</span>
          <span>Vulnerability {breakdown.vulnerability}</span>
          <span>Deficit {breakdown.resource_deficit}</span>
        </div>
      )}
    </div>
  );
}
