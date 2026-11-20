import React from 'react';
import { cn } from '@/utils/cn';
import { FolderOpen } from 'lucide-react';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center p-8 rounded-xl border border-border-subtle bg-surface-primary shadow-xs my-4',
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-surface-secondary flex items-center justify-center text-content-muted mb-4 border border-border-subtle">
        {icon || <FolderOpen className="w-6 h-6 text-brand" />}
      </div>
      <h3 className="text-base font-semibold text-content-primary mb-1">{title}</h3>
      <p className="text-sm text-content-secondary max-w-sm mb-5 leading-relaxed">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
