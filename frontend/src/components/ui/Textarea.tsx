import React, { forwardRef } from 'react';
import { cn } from '@/utils/cn';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, disabled, rows = 3, ...props }, ref) => {
    const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-xs font-semibold text-content-primary select-none"
          >
            {label}
          </label>
        )}
        <textarea
          id={textareaId}
          ref={ref}
          rows={rows}
          disabled={disabled}
          className={cn(
            'w-full rounded-lg p-3 text-sm bg-surface-primary text-content-primary border transition-all duration-120 ease-standard',
            'placeholder:text-content-muted',
            'focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent',
            'disabled:opacity-50 disabled:cursor-not-allowed resize-y',
            error
              ? 'border-status-error focus:ring-status-error animate-shake-error'
              : 'border-border-subtle hover:border-border-muted',
            className
          )}
          {...props}
        />
        {error ? (
          <p className="text-xs text-status-error font-medium" role="alert">
            {error}
          </p>
        ) : helperText ? (
          <p className="text-xs text-content-muted">{helperText}</p>
        ) : null}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
