import React from 'react';
import { cn } from '@/utils/cn';

export interface ConfidenceIndicatorProps {
  score: number; // 0.0 to 1.0
  showBar?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({
  score,
  showBar = true,
  size = 'sm',
  className,
}) => {
  const percentage = Math.round(Math.min(Math.max(score, 0), 1) * 100);

  let textColor = 'text-emerald-500';
  let barColor = 'bg-emerald-500';
  let label = 'High Grounding';

  if (score < 0.5) {
    textColor = 'text-rose-500';
    barColor = 'bg-rose-500';
    label = 'Low Confidence';
  } else if (score < 0.75) {
    textColor = 'text-amber-500';
    barColor = 'bg-amber-500';
    label = 'Moderate Confidence';
  }

  const barClasses = size === 'sm' ? 'w-20 h-1.5' : 'w-28 h-2';

  return (
    <div className={cn('inline-flex flex-col gap-1', className)} title={`${label} (${percentage}%)`}>
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="text-[11px] font-semibold text-content-secondary">Confidence</span>
        <span className={cn('font-mono font-bold text-xs', textColor)}>
          {percentage}%
        </span>
      </div>
      {showBar && (
        <div className={cn('rounded-full bg-surface-secondary overflow-hidden border border-border-subtle', barClasses)}>
          <div
            className={cn('h-full rounded-full transition-all duration-300', barColor)}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  );
};
