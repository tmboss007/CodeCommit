'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
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

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="border-b border-slate-800 bg-slate-950/95">
      <div className="mx-auto flex max-w-[88rem] flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="min-w-0">
          <div className="text-sm font-semibold tracking-[0.22em] text-white">CODECOMMIT</div>
          <div className="truncate text-xs text-slate-400">Emergency Resource Orchestration Platform</div>
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap gap-1">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? 'page' : undefined}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm',
                  active ? 'bg-slate-100 text-slate-950' : 'text-slate-300 hover:bg-slate-800',
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
