import type { Metadata } from 'next';
import './globals.css';
import { Nav } from '../components/Nav';

export const metadata: Metadata = {
  metadataBase: new URL('http://localhost:3000'),
  title: 'CodeCommit — Emergency Resource Orchestration',
  description: 'Real-time decision support for coordinating emergency resources across changing disaster situations.',
  openGraph: {
    title: 'CodeCommit — Emergency Resource Orchestration',
    description: 'Real-time decision support for coordinating emergency resources across changing disaster situations.',
    siteName: 'CodeCommit',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <Nav />
        <main className="mx-auto max-w-[88rem] px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
