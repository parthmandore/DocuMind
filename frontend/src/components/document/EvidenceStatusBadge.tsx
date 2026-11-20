import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, MinusCircle, HelpCircle } from 'lucide-react';
import { cn } from '@/utils/cn';

export type BackendEvidenceStatus =
  | 'SUPPORTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNSUPPORTED'
  | 'CONTRADICTED'
  | 'INSUFFICIENT_EVIDENCE';

export interface EvidenceStatusBadgeProps {
  status: BackendEvidenceStatus | string;
  size?: 'sm' | 'md';
  showIcon?: boolean;
  className?: string;
}

export const EvidenceStatusBadge: React.FC<EvidenceStatusBadgeProps> = ({
  status,
  size = 'sm',
  showIcon = true,
  className,
}) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-500/15 text-slate-400 border-slate-500/30';
  let icon: React.ReactNode = null;
  let label = status;

  switch (norm) {
    case 'SUPPORTED':
      colorClasses =
        'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
      label = 'Supported';
      break;

    case 'PARTIALLY_SUPPORTED':
      colorClasses =
        'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30';
      icon = <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
      label = 'Partially Supported';
      break;

    case 'CONTRADICTED':
      colorClasses =
        'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30';
      icon = <XCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />;
      label = 'Contradicted';
      break;

    case 'UNSUPPORTED':
      // Strictly neutral styling — NEVER visually represent as verified
      colorClasses =
        'bg-slate-500/15 text-slate-500 dark:text-slate-400 border-slate-500/30';
      icon = <MinusCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
      label = 'Unsupported';
      break;

    case 'INSUFFICIENT_EVIDENCE':
      colorClasses =
        'bg-slate-500/15 text-slate-500 dark:text-slate-400 border-slate-500/30';
      icon = <HelpCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
      label = 'Insufficient Evidence';
      break;

    default:
      icon = <MinusCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
      label = status;
      break;
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs gap-1.5' : 'px-2.5 py-1 text-sm gap-2';

  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full border select-none transition-colors',
        colorClasses,
        sizeClasses,
        className
      )}
    >
      {showIcon && icon}
      <span>{label}</span>
    </span>
  );
};
