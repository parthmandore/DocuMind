import React from 'react';
import { getDocumentStatusLabel } from '@/hooks/useJobPolling';
import type { DocumentStatus } from '@/types/api';
import { cn } from '@/utils/cn';

export interface ProcessingStageLabelProps {
  status: DocumentStatus | string;
  errorMessage?: string | null;
  className?: string;
}

export const ProcessingStageLabel: React.FC<ProcessingStageLabelProps> = ({
  status,
  errorMessage,
  className,
}) => {
  const label = getDocumentStatusLabel(status, errorMessage);

  return (
    <span className={cn('text-xs text-content-secondary font-medium', className)}>
      {label}
    </span>
  );
};
