'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

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
    <header className="border-b border-slate-800 bg-slate-900">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link href="/" className="min-w-0">
          <div className="text-lg font-bold tracking-[0.18em] text-white">CODECOMMIT</div>
          <div className="truncate text-xs text-slate-400">Emergency Resource Orchestration Platform</div>
        </Link>
        <nav className="flex flex-wrap gap-1">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded px-3 py-1.5 text-sm ${active ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}
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
