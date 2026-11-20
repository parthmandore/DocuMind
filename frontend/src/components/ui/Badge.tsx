import React from 'react';
import { cn } from '@/utils/cn';
import { Loader2 } from 'lucide-react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'error'
  | 'information'
  | 'neutral'
  | 'processing'
  | 'brand';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'neutral',
  size = 'sm',
  icon,
  children,
  ...props
}) => {
  const variantClasses: Record<BadgeVariant, string> = {
    success:
      'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
    warning:
      'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
    error:
      'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30',
    information:
      'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30',
    neutral:
      'bg-surface-secondary text-content-secondary border-border-subtle',
    processing:
      'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30',
    brand:
      'bg-brand/15 text-brand border-brand/30 shadow-xs shadow-brand/10',
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1.5',
    md: 'px-2.5 py-1 text-sm gap-2',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full border select-none transition-colors',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {variant === 'processing' && !icon ? (
        <Loader2 className="w-3 h-3 animate-spin shrink-0" />
      ) : (
        icon && <span className="inline-flex shrink-0">{icon}</span>
      )}
      <span>{children}</span>
    </span>
  );
};
