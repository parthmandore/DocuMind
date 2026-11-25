import React from 'react';
import { cn } from '@/utils/cn';
import type { DocumentStatus } from '@/types/api';

export interface IndexingProgressIndicatorProps {
  status: DocumentStatus | string;
  isPaused?: boolean;
  className?: string;
  embeddingProgress?: {
    completed: number;
    total: number;
    percent?: number;
  };
  showSearchableBadge?: boolean;
}

const STAGES = [
  { key: 'PENDING', label: 'Queued' },
  { key: 'PROCESSING', label: 'Extracting' },
  { key: 'CHUNKED', label: 'Search Index' },
  { key: 'EMBEDDING', label: 'Embedding' },
  { key: 'COMPLETED', label: 'Ready' },
];

export const IndexingProgressIndicator: React.FC<IndexingProgressIndicatorProps> = ({
  status,
  isPaused = false,
  className,
  embeddingProgress,
  showSearchableBadge = true,
}) => {
  const norm = (status || '').toUpperCase();
  const isFailed = norm === 'FAILED';

  const getStageIndex = (s: string): number => {
    switch (s) {
      case 'PENDING':
        return 0;
      case 'PROCESSING':
      case 'EXTRACTED':
        return 1;
      case 'CHUNKED':
        return 2;
      case 'EMBEDDING':
      case 'INDEXED':
        return 3;
      case 'COMPLETED':
        return 4;
      default:
        return 0;
    }
  };

  const currentIndex = getStageIndex(norm);
  const isLexicalReady =
    norm === 'CHUNKED' || norm === 'EMBEDDING' || norm === 'INDEXED' || norm === 'COMPLETED';

  let progressLabel = `${Math.round(((currentIndex + 1) / STAGES.length) * 100)}%`;
  if (norm === 'EMBEDDING' && embeddingProgress && embeddingProgress.total > 0) {
    const pct =
      embeddingProgress.percent ??
      Math.round((embeddingProgress.completed / embeddingProgress.total) * 100);
    progressLabel = `${embeddingProgress.completed}/${embeddingProgress.total} (${pct}%)`;
  }

  return (
    <div className={cn('w-full space-y-2', className)}>
      <div className="flex items-center justify-between text-[11px] font-semibold text-content-secondary">
        <span className="flex items-center gap-1.5">
          <span>Ingestion</span>
          {showSearchableBadge && isLexicalReady && norm !== 'COMPLETED' && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Searchable
            </span>
          )}
        </span>
        <span className={isFailed ? 'text-status-error' : isPaused ? 'text-amber-400 font-mono font-semibold' : 'text-brand font-mono font-semibold'}>
          {isFailed ? 'Error' : isPaused ? 'Paused' : progressLabel}
        </span>
      </div>

      <div className="grid grid-cols-5 gap-1.5">
        {STAGES.map((stage, idx) => {
          const isDone = currentIndex > idx || norm === 'COMPLETED';
          const isCurrent = currentIndex === idx && !isFailed && norm !== 'COMPLETED';

          return (
            <div key={stage.key} className="space-y-1">
              <div
                className={cn(
                  'h-1.5 w-full rounded-full transition-all duration-200 ease-standard',
                  isFailed
                    ? 'bg-status-error/30'
                    : isDone
                    ? 'bg-brand shadow-xs shadow-brand/20'
                    : isCurrent && isPaused
                    ? 'bg-amber-500/60'
                    : isCurrent
                    ? 'bg-brand/60 animate-pulse'
                    : 'bg-surface-secondary'
                )}
              />
              <span
                className={cn(
                  'block text-[10px] text-center truncate',
                  isDone
                    ? 'text-content-primary font-medium'
                    : isCurrent
                    ? 'text-brand-light font-semibold'
                    : 'text-content-muted'
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
