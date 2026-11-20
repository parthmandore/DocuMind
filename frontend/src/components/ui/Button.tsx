import React, { forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils/cn';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

export const buttonVariants = cva(
  'inline-flex items-center justify-center font-medium transition-all duration-120 ease-standard focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none rounded-lg active:scale-[0.97] transform-gpu',
  {
    variants: {
      variant: {
        primary:
          'bg-brand text-[#08090B] font-semibold hover:bg-brand-hover active:bg-brand-hover shadow-sm shadow-brand/20 hover:shadow-md hover:shadow-brand/25',
        secondary:
          'bg-surface-primary text-content-primary hover:bg-surface-hover border border-border-subtle shadow-xs hover:border-border-muted',
        outline:
          'border border-border-muted text-content-primary hover:bg-surface-hover hover:text-content-primary',
        ghost:
          'text-content-secondary hover:text-content-primary hover:bg-surface-hover',
        destructive:
          'bg-status-error text-white hover:opacity-90 shadow-sm',
        danger:
          'bg-status-error text-white hover:opacity-90 shadow-sm',
        subtle:
          'bg-brand/15 text-brand border border-brand/30 hover:bg-brand/25 font-medium shadow-xs shadow-brand/10',
      },
      size: {
        sm: 'h-8 px-3 text-xs gap-1.5 min-h-[32px]',
        md: 'h-9 px-4 text-sm gap-2 min-h-[36px]',
        lg: 'h-10 px-6 text-base gap-2.5 min-h-[40px]',
        icon: 'h-9 w-9 p-0 min-w-[36px] min-h-[36px]',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  icon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      isLoading = false,
      icon,
      children,
      disabled,
      'aria-label': ariaLabel,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size, className }))}
        disabled={disabled || isLoading}
        aria-busy={isLoading}
        aria-disabled={disabled || isLoading}
        aria-label={ariaLabel}
        {...props}
      >
        {isLoading ? (
          <LoadingSpinner size="sm" className="mr-1.5" />
        ) : (
          icon && <span className="inline-flex shrink-0">{icon}</span>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
