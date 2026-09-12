'use client';

import { useEffect } from 'react';
import { Button } from './button';

export function Dialog({
  title,
  children,
  onClose,
  wide,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" role="presentation" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        className={`max-h-[90vh] overflow-auto border border-line bg-white p-5 ${wide ? 'w-full max-w-3xl' : 'w-full max-w-md'}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 id="dialog-title" className="text-[16px] font-semibold text-ink">{title}</h2>
          <Button variant="ghost" onClick={onClose} aria-label="Close dialog">Close</Button>
        </div>
        {children}
      </div>
    </div>
  );
}
