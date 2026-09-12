import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AppShell } from '../components/AppShell';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  metadataBase: new URL('http://localhost:3000'),
  title: 'CodeCommit — Emergency Operations Platform',
  description: 'Decision support for coordinating emergency resources across changing disaster situations.',
  openGraph: {
    title: 'CodeCommit — Emergency Operations Platform',
    description: 'Decision support for coordinating emergency resources across changing disaster situations.',
    siteName: 'CodeCommit',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen bg-bg text-ink antialiased`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
