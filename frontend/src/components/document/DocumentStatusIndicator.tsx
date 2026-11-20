import React from 'react';
import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { DocumentStatus } from '@/types/api';

export interface DocumentStatusIndicatorProps {
  status: DocumentStatus | string;
  size?: 'sm' | 'md';
  showLabel?: boolean;
  className?: string;
}

export const DocumentStatusIndicator: React.FC<DocumentStatusIndicatorProps> = ({
  status,
  size = 'sm',
  showLabel = true,
  className,
}) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-500/15 text-slate-400 border-slate-500/30';
  let icon: React.ReactNode = null;
  let label = status;

  switch (norm) {
    case 'COMPLETED':
    case 'INDEXED':
      colorClasses =
        'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
      icon = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
      label = 'Ready';
      break;

    case 'PROCESSING':
    case 'EXTRACTED':
    case 'CHUNKED':
    case 'EMBEDDING':
      colorClasses =
        'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30';
      icon = <Loader2 className="w-3.5 h-3.5 text-indigo-500 animate-spin shrink-0" />;
      label = norm === 'EMBEDDING' ? 'Embedding' : norm === 'CHUNKED' ? 'Chunking' : 'Processing';
      break;

    case 'PENDING':
      colorClasses =
        'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30';
      icon = <Clock className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
      label = 'Queued';
      break;

    case 'FAILED':
      colorClasses =
        'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30';
      icon = <AlertCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />;
      label = 'Failed';
      break;

    default:
      icon = <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />;
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
      {icon}
      {showLabel && <span>{label}</span>}
    </span>
  );
};
