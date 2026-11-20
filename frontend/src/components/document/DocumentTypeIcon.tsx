import React from 'react';
import { FileText, FileCode, Table2, File } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface DocumentTypeIconProps {
  filename?: string;
  mimeType?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const DocumentTypeIcon: React.FC<DocumentTypeIconProps> = ({
  filename = '',
  mimeType = '',
  size = 'md',
  className,
}) => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';

  const sizeClasses = {
    sm: 'w-7 h-7 p-1.5',
    md: 'w-9 h-9 p-2',
    lg: 'w-11 h-11 p-2.5',
  };

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-5 h-5',
    lg: 'w-6 h-6',
  };

  if (ext === 'docx' || mimeType.includes('wordprocessingml') || mimeType.includes('docx')) {
    return (
      <div
        className={cn(
          'rounded-lg bg-blue-500/15 text-blue-500 flex items-center justify-center shrink-0 border border-blue-500/20',
          sizeClasses[size],
          className
        )}
        title="Word Document (.docx)"
      >
        <FileText className={iconSizes[size]} />
      </div>
    );
  }

  if (ext === 'pdf' || mimeType.includes('pdf')) {
    return (
      <div
        className={cn(
          'rounded-lg bg-rose-500/15 text-rose-500 flex items-center justify-center shrink-0 border border-rose-500/20',
          sizeClasses[size],
          className
        )}
        title="PDF Document"
      >
        <FileText className={iconSizes[size]} />
      </div>
    );
  }

  if (['csv', 'xlsx', 'xls', 'tsv'].includes(ext)) {
    return (
      <div
        className={cn(
          'rounded-lg bg-emerald-500/15 text-emerald-500 flex items-center justify-center shrink-0 border border-emerald-500/20',
          sizeClasses[size],
          className
        )}
        title="Tabular Data"
      >
        <Table2 className={iconSizes[size]} />
      </div>
    );
  }

  if (['md', 'markdown', 'json', 'py', 'ts'].includes(ext)) {
    return (
      <div
        className={cn(
          'rounded-lg bg-indigo-500/15 text-indigo-500 flex items-center justify-center shrink-0 border border-indigo-500/20',
          sizeClasses[size],
          className
        )}
        title="Structured / Code Document"
      >
        <FileCode className={iconSizes[size]} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'rounded-lg bg-surface-secondary text-content-secondary flex items-center justify-center shrink-0 border border-border-subtle',
        sizeClasses[size],
        className
      )}
      title="Text Document"
    >
      <File className={iconSizes[size]} />
    </div>
  );
};
