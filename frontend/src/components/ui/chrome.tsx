import type { ReactNode } from 'react';
import { cn } from '../../lib/utils';

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
      <div>
        <h1 className="text-page tracking-[-0.02em] text-ink">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-muted">{description}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Section({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('min-w-0', className)}>
      <h2 className="mb-3 flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
        <span className="h-1.5 w-1.5 bg-accent" aria-hidden />
        {title}
      </h2>
      {children}
    </section>
  );
}

export function MetricStrip({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return (
    <div className="grid grid-cols-2 border-y border-line bg-white md:grid-cols-3 xl:grid-cols-6">
      {items.map((item, index) => (
        <div key={item.label} className="border-line px-4 py-3.5 first:bg-surface2 md:border-l md:first:border-l-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">{item.label}</div>
          <div className="mt-1 text-metric tabular-nums text-ink">{item.value ?? 0}</div>
        </div>
      ))}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div role="alert" className="border-l-4 border-critical bg-white px-3 py-2.5 text-sm text-critical shadow-[0_1px_2px_rgb(23_26_31/6%)]">
      {message}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="border border-dashed border-line bg-surface2 px-4 py-7">
      <div className="text-sm font-medium text-ink">{title}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div role="status" className="border-l-4 border-success bg-white px-3 py-2.5 text-sm text-ink shadow-[0_1px_2px_rgb(23_26_31/6%)]">
      {children}
    </div>
  );
}
