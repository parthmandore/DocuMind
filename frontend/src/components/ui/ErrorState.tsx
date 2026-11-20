import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';
import { Button } from './Button';
import { cn } from '@/utils/cn';

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  message: string;
  onRetry?: () => void;
  isRetryable?: boolean;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  className,
  title = 'An Error Occurred',
  message,
  onRetry,
  isRetryable = true,
  ...props
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center p-8 rounded-xl border border-status-error/30 bg-surface-primary shadow-sm my-4',
        className
      )}
      {...props}
    >
      <div className="w-12 h-12 rounded-full bg-status-error/15 flex items-center justify-center text-status-error mb-4">
        <AlertOctagon className="w-6 h-6" />
      </div>
      <h4 className="text-base font-semibold text-content-primary mb-1">{title}</h4>
      <p className="text-xs sm:text-sm text-content-secondary max-w-md mb-5 leading-relaxed">
        {message}
      </p>
      {onRetry && isRetryable && (
        <Button
          variant="secondary"
          size="sm"
          onClick={onRetry}
          icon={<RotateCcw className="w-3.5 h-3.5" />}
        >
          Try Again
        </Button>
      )}
    </div>
  );
};
