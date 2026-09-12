'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useOps } from '../lib/ops-runtime';
import { cn } from '../lib/utils';

const links = [
  { href: '/', label: 'Command Center' },
  { href: '/incidents', label: 'Incidents' },
  { href: '/resources', label: 'Resources' },
  { href: '/coordination', label: 'Coordination' },
  { href: '/agents', label: 'Agents' },
  { href: '/audit', label: 'Audit' },
  { href: '/simulation', label: 'Scenario Simulator' },
];

function connectionLabel(connection: string) {
  if (connection === 'live') return 'CONNECTED';
  if (connection === 'polling') return 'POLLING FALLBACK';
  return 'RECONNECTING';
}

export function Nav() {
  const pathname = usePathname();
  const { connection } = useOps();
  const live = connection === 'live';
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-[88rem] flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="min-w-0">
          <div className="text-sm font-semibold text-brand">CODECOMMIT</div>
          <div className="truncate text-[13px] text-muted">Emergency Operations Platform</div>
        </Link>
        <div className="flex flex-wrap items-center gap-4">
          <span
            className="inline-flex items-center gap-1.5 text-[12px] font-medium text-muted"
            aria-live="polite"
          >
            <span
              aria-hidden
              className={cn('h-1.5 w-1.5 rounded-full', live ? 'bg-success' : 'bg-neutral')}
            />
            {connectionLabel(connection)}
          </span>
          <nav aria-label="Primary" className="flex flex-wrap gap-1">
            {links.map((l) => {
              const active = pathname === l.href;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'border-b-2 px-2.5 py-1.5 text-sm',
                    active ? 'border-brand font-semibold text-ink' : 'border-transparent text-muted hover:text-ink',
                  )}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
