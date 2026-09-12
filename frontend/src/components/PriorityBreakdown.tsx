import { formatScore, severityTier } from '../lib/ops';
import { Badge } from './ui/badge';

export function PriorityBreakdown({ score }: { score: number; breakdown?: Record<string, number> | null }) {
  const tier = severityTier(score);
  return (
    <div className="text-right">
      <Badge tone={tier.tone}>{tier.label}</Badge>
      <div className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{formatScore(score, 2)}</div>
    </div>
  );
}
