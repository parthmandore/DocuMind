import React from 'react';
import { DocumentTypeIcon } from './DocumentTypeIcon';
import { DocumentStatusIndicator } from './DocumentStatusIndicator';
import { cn } from '@/utils/cn';
import type { DocumentStatus } from '@/types/api';

export interface DocumentMetadataRowProps {
  id: string;
  title: string;
  filename: string;
  status: DocumentStatus | string;
  totalPages?: number;
  totalChunks?: number;
  fileSizeBytes?: number;
  uploadedAt?: string;
  isSelected?: boolean;
  onClick?: () => void;
  actions?: React.ReactNode;
  className?: string;
}

export const DocumentMetadataRow: React.FC<DocumentMetadataRowProps> = ({
  title,
  filename,
  status,
  totalPages,
  totalChunks,
  fileSizeBytes,
  uploadedAt,
  isSelected = false,
  onClick,
  actions,
  className,
}) => {
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '--';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr?: string): string => {
    if (!dateStr) return '--';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      className={cn(
        'flex items-center justify-between p-3.5 rounded-xl border transition-all text-left',
        isSelected
          ? 'bg-brand/10 border-brand shadow-sm'
          : 'bg-surface-primary border-border-subtle hover:bg-surface-secondary/70 hover:border-border-muted shadow-xs',
        onClick && 'cursor-pointer active:scale-[0.99]',
        className
      )}
    >
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <DocumentTypeIcon filename={filename} size="sm" />
        <div className="min-w-0 flex-1 space-y-0.5">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-content-primary truncate">
              {filename || title}
            </h4>
            <DocumentStatusIndicator status={status} size="sm" showLabel={false} />
          </div>
          <div className="flex items-center gap-3 text-xs text-content-muted font-mono flex-wrap">
            {totalPages !== undefined && <span>{totalPages} page{totalPages !== 1 ? 's' : ''}</span>}
            {totalChunks !== undefined && <span>• {totalChunks} chunks</span>}
            {fileSizeBytes !== undefined && <span>• {formatFileSize(fileSizeBytes)}</span>}
            {uploadedAt && <span className="font-sans">• {formatDate(uploadedAt)}</span>}
          </div>
        </div>
      </div>

      {actions && <div className="flex items-center gap-2 shrink-0 ml-3">{actions}</div>}
    </div>
  );
};
