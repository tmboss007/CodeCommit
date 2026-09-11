export function PriorityBreakdown({ score, breakdown }: { score: number; breakdown?: Record<string, number> | null }) {
  const color = score >= 80 ? 'text-red-400' : score >= 60 ? 'text-orange-300' : 'text-sky-300';
  return (
    <div>
      <div className={`text-2xl font-bold ${color}`}>{Number(score || 0).toFixed(0)}/100</div>
      {breakdown && (
        <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-slate-400">
          <span>Severity {breakdown.severity}</span>
          <span>Population {breakdown.affected_population}</span>
          <span>Vulnerability {breakdown.vulnerability}</span>
          <span>Deficit {breakdown.resource_deficit}</span>
          <span>Time {breakdown.time_criticality}</span>
        </div>
      )}
    </div>
  );
}
