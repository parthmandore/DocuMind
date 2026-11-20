import React, { forwardRef } from 'react';
import { Search, X } from 'lucide-react';
import { cn } from '@/utils/cn';

export interface SearchInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  label?: string;
}

export const SearchInput = forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, value, onChange, onClear, placeholder = 'Search documents, topics, or claims...', label, ...props }, ref) => {
    const handleClear = () => {
      onChange('');
      if (onClear) onClear();
    };

    return (
      <div className="w-full space-y-1.5 text-left">
        {label && (
          <label className="block text-xs font-semibold text-content-primary select-none">
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          <div className="absolute left-3 flex items-center pointer-events-none text-content-muted">
            <Search className="w-4 h-4" />
          </div>
          <input
            ref={ref}
            type="search"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={cn(
              'w-full h-9 pl-9 pr-8 rounded-lg text-sm bg-surface-primary text-content-primary border border-border-subtle transition-all duration-120 ease-standard',
              'placeholder:text-content-muted',
              'hover:border-border-muted focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              className
            )}
            {...props}
          />
          {value && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-1.5 min-w-[32px] min-h-[32px] p-1.5 flex items-center justify-center rounded-md text-content-muted hover:text-content-primary hover:bg-surface-hover transition-all duration-100 active:scale-95"
              aria-label="Clear search query"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    );
  }
);

SearchInput.displayName = 'SearchInput';
