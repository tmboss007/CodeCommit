export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded border border-red-800 bg-red-950/70 p-3 text-sm text-red-200">
      {message}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded border border-dashed border-slate-700 p-6 text-center">
      <div className="text-sm font-medium text-slate-200">{title}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function kindForActor(agent?: string) {
  const name = (agent || '').toLowerCase();
  if (name.includes('service') || name.includes('engine') || name.includes('evaluator') || name.includes('optimization')) {
    return 'Decision Service';
  }
  if (name.includes('approval') || name.includes('operator')) {
    return 'Operator';
  }
  if (name.includes('agent')) {
    return 'Agent';
  }
  return 'System';
}
