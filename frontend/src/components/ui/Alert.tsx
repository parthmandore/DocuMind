import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { cn } from '@/utils/cn';

export type AlertVariant = 'success' | 'warning' | 'error' | 'info';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
  title?: string;
  icon?: React.ReactNode;
}

export const Alert: React.FC<AlertProps> = ({
  className,
  variant = 'info',
  title,
  icon,
  children,
  ...props
}) => {
  const variantStyles: Record<
    AlertVariant,
    { container: string; icon: React.ReactNode; title: string }
  > = {
    success: {
      container:
        'bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-300',
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />,
      title: 'text-emerald-900 dark:text-emerald-200',
    },
    warning: {
      container:
        'bg-amber-500/10 border-amber-500/30 text-amber-800 dark:text-amber-300',
      icon: <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />,
      title: 'text-amber-900 dark:text-amber-200',
    },
    error: {
      container:
        'bg-rose-500/10 border-rose-500/30 text-rose-800 dark:text-rose-300',
      icon: <AlertCircle className="w-5 h-5 text-rose-500 shrink-0" />,
      title: 'text-rose-900 dark:text-rose-200',
    },
    info: {
      container:
        'bg-blue-500/10 border-blue-500/30 text-blue-800 dark:text-blue-300',
      icon: <Info className="w-5 h-5 text-blue-500 shrink-0" />,
      title: 'text-blue-900 dark:text-blue-200',
    },
  };

  const style = variantStyles[variant];

  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 p-4 rounded-xl border text-sm leading-relaxed',
        style.container,
        className
      )}
      {...props}
    >
      <span className="mt-0.5">{icon || style.icon}</span>
      <div className="flex-1 space-y-1">
        {title && <h5 className={cn('font-semibold', style.title)}>{title}</h5>}
        <div className="text-xs sm:text-sm">{children}</div>
      </div>
    </div>
  );
};
