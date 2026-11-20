import React from 'react';
import { cn } from '@/utils/cn';

export interface TabItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  badge?: string | number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  variant?: 'underline' | 'pills';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
  className,
}) => {
  return (
    <div
      role="tablist"
      className={cn(
        'flex items-center gap-1 overflow-x-auto select-none no-scrollbar',
        variant === 'underline' && 'border-b border-border-subtle',
        variant === 'pills' && 'p-1 rounded-xl bg-surface-secondary/70 border border-border-subtle',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'flex items-center gap-2 px-3.5 py-2 min-h-[36px] text-xs font-semibold whitespace-nowrap transition-all duration-150 ease-standard rounded-lg active:scale-[0.98]',
              variant === 'underline' && [
                'rounded-b-none border-b-2 -mb-[1px]',
                isActive
                  ? 'border-brand text-brand'
                  : 'border-transparent text-content-secondary hover:text-content-primary hover:border-border-muted',
              ],
              variant === 'pills' && [
                isActive
                  ? 'bg-brand/15 text-brand border border-brand/30 shadow-xs'
                  : 'text-content-secondary hover:text-content-primary hover:bg-surface-hover/50 border border-transparent',
              ]
            )}
          >
            {tab.icon && <span className="w-3.5 h-3.5 shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded-full text-[10px] font-mono',
                  isActive ? 'bg-brand/25 text-brand font-semibold' : 'bg-surface-secondary text-content-muted'
                )}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
