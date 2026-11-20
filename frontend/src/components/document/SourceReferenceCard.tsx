import React from 'react';
import { FileText, Layers } from 'lucide-react';
import { PageNumberIndicator } from './PageNumberIndicator';
import { cn } from '@/utils/cn';

export interface SourceReferenceCardProps {
  documentTitle: string;
  filename?: string;
  snippet: string;
  pageNumber: number;
  score?: number;
  bboxesCount?: number;
  isSelected?: boolean;
  onClick?: () => void;
  className?: string;
}

export const SourceReferenceCard: React.FC<SourceReferenceCardProps> = ({
  documentTitle,
  filename,
  snippet,
  pageNumber,
  score,
  bboxesCount,
  isSelected = false,
  onClick,
  className,
}) => {
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      className={cn(
        'rounded-xl border p-4 text-left transition-all',
        isSelected
          ? 'bg-brand/10 border-brand shadow-sm'
          : 'bg-surface-primary border-border-subtle hover:border-border-muted shadow-sm',
        onClick && 'cursor-pointer active:scale-[0.99]',
        className
      )}
    >
      {/* Header Metadata */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 truncate">
          <FileText className="w-3.5 h-3.5 text-brand-light shrink-0" />
          <span className="text-xs font-semibold text-content-primary truncate">
            {filename || documentTitle}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <PageNumberIndicator pageNumber={pageNumber} />
          {score !== undefined && (
            <span className="text-[10px] font-mono text-content-muted">
              {Math.round(score * 100)}% match
            </span>
          )}
        </div>
      </div>

      {/* Verbatim Excerpt */}
      <blockquote className="text-xs text-content-secondary line-clamp-3 leading-relaxed border-l-2 border-brand/40 pl-2.5 my-2 italic">
        "{snippet}"
      </blockquote>

      {/* Footer Details */}
      {bboxesCount !== undefined && bboxesCount > 0 && (
        <div className="flex items-center gap-1 text-[11px] text-content-muted mt-2 pt-2 border-t border-border-subtle/50">
          <Layers className="w-3 h-3 text-content-muted" />
          <span>{bboxesCount} bounding box highlight{bboxesCount > 1 ? 's' : ''} available</span>
        </div>
      )}
    </div>
  );
};
