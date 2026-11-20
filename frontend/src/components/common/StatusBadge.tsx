import React from 'react';
import { cn } from '@/utils/cn';
import { CheckCircle2, AlertTriangle, XCircle, Clock, Loader2, MinusCircle } from 'lucide-react';

export type StatusType =
  | 'COMPLETED'
  | 'PROCESSING'
  | 'EXTRACTED'
  | 'CHUNKED'
  | 'EMBEDDING'
  | 'INDEXED'
  | 'PENDING'
  | 'FAILED'
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'CONTRADICTED'
  | 'INSUFFICIENT'
  | 'healthy'
  | 'degraded'
  | 'offline';

export interface StatusBadgeProps {
  status: StatusType | string;
  label?: string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'sm',
  showIcon = true,
  className,
}) => {
  const norm = (status || '').toUpperCase();

  let colorClasses =
    'bg-surface-secondary text-content-secondary border-border-subtle';
  let icon: React.ReactNode = null;
  let defaultLabel = status;

  switch (norm) {
    case 'COMPLETED':
    case 'HEALTHY':
    case 'SUPPORTED':
    case 'ONLINE':
      colorClasses =
        'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
      defaultLabel =
        norm === 'SUPPORTED' ? 'Supported' : norm === 'HEALTHY' ? 'Healthy' : 'Completed';
      break;

    case 'PARTIALLY_SUPPORTED':
    case 'DEGRADED':
    case 'EXTRACTED':
    case 'CHUNKED':
    case 'EMBEDDING':
      colorClasses =
        'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30';
      icon = <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
      defaultLabel =
        norm === 'PARTIALLY_SUPPORTED'
          ? 'Partially Supported'
          : norm === 'DEGRADED'
          ? 'Degraded'
          : norm;
      break;

    case 'PROCESSING':
    case 'PENDING':
    case 'INDEXED':
      colorClasses =
        'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30';
      icon = <Loader2 className="w-3.5 h-3.5 text-indigo-500 animate-spin shrink-0" />;
      defaultLabel = norm === 'PROCESSING' ? 'Processing' : norm === 'PENDING' ? 'Pending' : 'Indexed';
      break;

    case 'CONTRADICTED':
    case 'FAILED':
    case 'OFFLINE':
      colorClasses =
        'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30';
      icon = <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />;
      defaultLabel = norm === 'CONTRADICTED' ? 'Contradicted' : norm === 'FAILED' ? 'Failed' : 'Offline';
      break;

    case 'UNSUPPORTED':
    case 'INSUFFICIENT':
      colorClasses =
        'bg-slate-500/15 text-slate-500 dark:text-slate-400 border-slate-500/30';
      icon = <MinusCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
      defaultLabel = norm === 'UNSUPPORTED' ? 'Unsupported' : 'Insufficient Evidence';
      break;

    default:
      icon = <Clock className="w-3.5 h-3.5 text-content-muted shrink-0" />;
      defaultLabel = status;
      break;
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs gap-1.5' : 'px-2.5 py-1 text-sm gap-2';

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full border transition-colors select-none',
        colorClasses,
        sizeClasses,
        className
      )}
    >
      {showIcon && icon}
      <span>{label || defaultLabel}</span>
    </span>
  );
};
