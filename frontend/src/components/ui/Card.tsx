import React from 'react';
import { cn } from '@/utils/cn';

// --- Base Card Component ---

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'subtle';
}

export const Card: React.FC<CardProps> = ({
  className,
  variant = 'default',
  children,
  ...props
}) => {
  const variantClasses = {
    default: 'bg-surface-primary border-border-subtle shadow-xs hover:border-border-muted transition-all duration-200',
    elevated: 'bg-surface-elevated border-border-subtle shadow-sm hover:shadow-md transition-all duration-200',
    subtle: 'bg-surface-secondary/70 border-border-subtle/80',
  };

  return (
    <div
      className={cn(
        'rounded-xl border transition-colors',
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div
    className={cn('flex items-center justify-between p-5 border-b border-border-subtle', className)}
    {...props}
  >
    {children}
  </div>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => <div className={cn('p-5', className)} {...props}>{children}</div>;

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div
    className={cn('flex items-center justify-between p-4 border-t border-border-subtle bg-surface-secondary/40 rounded-b-xl', className)}
    {...props}
  >
    {children}
  </div>
);

// --- Interactive Card Component ---

export interface InteractiveCardProps extends React.HTMLAttributes<HTMLDivElement> {
  selected?: boolean;
}

export const InteractiveCard: React.FC<InteractiveCardProps> = ({
  className,
  selected = false,
  children,
  ...props
}) => {
  return (
    <div
      role="button"
      tabIndex={0}
      className={cn(
        'rounded-xl border p-5 cursor-pointer transition-all duration-150 ease-standard select-none transform-gpu',
        'focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent',
        selected
          ? 'bg-brand/10 border-brand shadow-sm shadow-brand/10'
          : 'bg-surface-primary border-border-subtle hover:border-brand/40 hover:bg-surface-hover hover:-translate-y-0.5 shadow-sm active:scale-[0.985]',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

// --- Section Panel Component ---

export interface SectionPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export const SectionPanel: React.FC<SectionPanelProps> = ({
  className,
  title,
  subtitle,
  actions,
  children,
  ...props
}) => {
  return (
    <div
      className={cn('rounded-xl border border-border-subtle bg-surface-primary shadow-sm overflow-hidden', className)}
      {...props}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-5 border-b border-border-subtle gap-3">
        <div>
          <h3 className="text-base font-semibold text-content-primary leading-tight">{title}</h3>
          {subtitle && (
            <p className="text-xs text-content-secondary mt-0.5">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
};

// --- Metric Card Component ---

export interface MetricCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number | React.ReactNode;
  icon?: React.ReactNode;
  trend?: string;
  badge?: React.ReactNode;
  description?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  className,
  label,
  value,
  icon,
  trend,
  badge,
  description,
  ...props
}) => {
  return (
    <Card
      className={cn(
        'p-5 space-y-3 transition-all duration-180 ease-standard hover:border-border-muted hover:shadow-md hover:-translate-y-0.5 transform-gpu',
        className
      )}
      {...props}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-content-secondary uppercase tracking-wider">
          {label}
        </span>
        {icon && <div className="p-1.5 rounded-lg bg-brand/10 text-brand border border-brand/20 shrink-0">{icon}</div>}
      </div>
      <div className="flex items-baseline justify-between">
        <span className="text-2xl font-bold text-content-primary tracking-tight font-mono">
          {value}
        </span>
        {badge}
      </div>
      {(trend || description) && (
        <p className="text-xs text-content-secondary flex items-center gap-1.5 pt-1 border-t border-border-subtle/50">
          {trend && <span className="font-semibold text-brand">{trend}</span>}
          {description && <span>{description}</span>}
        </p>
      )}
    </Card>
  );
};
