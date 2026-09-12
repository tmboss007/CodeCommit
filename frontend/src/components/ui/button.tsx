import type { ButtonHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

type Variant = 'primary' | 'secondary' | 'success' | 'danger' | 'ghost' | 'outline';

const variants: Record<Variant, string> = {
  primary: 'bg-brand text-white hover:bg-[#1b2d40]',
  secondary: 'border border-line bg-white text-ink hover:bg-surface2',
  success: 'bg-success text-white hover:bg-[#145c3c]',
  danger: 'bg-critical text-white hover:bg-[#931c14]',
  ghost: 'bg-transparent text-muted hover:text-ink hover:bg-surface2',
  outline: 'border border-line bg-transparent text-ink hover:bg-surface2',
};

export function Button({
  variant = 'primary',
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        'inline-flex min-h-9 items-center justify-center rounded-[4px] px-3 py-2 text-sm font-medium shadow-[0_1px_1px_rgb(23_26_31/8%)] transition-[background-color,border-color,color,transform] duration-150 active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
