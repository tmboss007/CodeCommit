'use client';

import { OpsProvider } from '../lib/ops-runtime';
import { Nav } from './Nav';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <OpsProvider>
      <Nav />
      <main className="mx-auto max-w-[88rem] px-4 py-6">{children}</main>
    </OpsProvider>
  );
}
