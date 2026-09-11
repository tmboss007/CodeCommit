import type { ButtonHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

type Variant = 'primary' | 'secondary' | 'success' | 'danger' | 'ghost' | 'outline';

const variants: Record<Variant, string> = {
  primary: 'bg-sky-600 text-white hover:bg-sky-500',
  secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700',
  success: 'bg-emerald-700 text-white hover:bg-emerald-600',
  danger: 'bg-red-800 text-white hover:bg-red-700',
  ghost: 'bg-transparent text-slate-300 hover:bg-slate-800',
  outline: 'border border-slate-600 bg-transparent text-slate-100 hover:bg-slate-800',
};

export function Button({
  variant = 'primary',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-400 disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
