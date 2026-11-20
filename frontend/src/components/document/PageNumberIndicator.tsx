import React from 'react';
import { cn } from '@/utils/cn';

export interface PageNumberIndicatorProps {
  pageNumber: number;
  totalPages?: number;
  className?: string;
}

export const PageNumberIndicator: React.FC<PageNumberIndicatorProps> = ({
  pageNumber,
  totalPages,
  className,
}) => {
  return (
    <span
      className={cn(
        'inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium',
        'bg-surface-secondary text-content-secondary border border-border-subtle select-none',
        className
      )}
    >
      {totalPages ? `p. ${pageNumber}/${totalPages}` : `p. ${pageNumber}`}
    </span>
  );
};
