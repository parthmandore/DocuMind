import React from 'react';
import { getDocumentStatusLabel } from '@/hooks/useJobPolling';
import type { DocumentStatus } from '@/types/api';
import { cn } from '@/utils/cn';

export interface ProcessingStageLabelProps {
  status: DocumentStatus | string;
  className?: string;
}

export const ProcessingStageLabel: React.FC<ProcessingStageLabelProps> = ({
  status,
  className,
}) => {
  const label = getDocumentStatusLabel(status);

  return (
    <span className={cn('text-xs text-content-secondary font-medium', className)}>
      {label}
    </span>
  );
};
