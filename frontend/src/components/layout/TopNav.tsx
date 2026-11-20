import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useHealth } from '@/hooks/useHealth';
import { useTheme } from '@/context/ThemeContext';
import { RefreshCw, Sun, Moon, HelpCircle, Menu } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SupportModal } from './SupportModal';

interface TopNavProps {
  onToggleMobileMenu?: () => void;
}

const routeTitles: Record<string, { title: string; subtitle: string; category: string }> = {
  '/': {
    title: 'Dashboard',
    subtitle: 'Corpus synthesis & operational intelligence',
    category: 'Overview',
  },
  '/documents': {
    title: 'Document Library',
    subtitle: 'Corpus repository & structural layout ingestion',
    category: 'Corpus',
  },
  '/research': {
    title: 'Research Workspace',
    subtitle: 'Grounded inquiry & two-stage citation verification',
    category: 'Intelligence',
  },
  '/conversations': {
    title: 'Conversation Threads',
    subtitle: 'Persistent interactive multi-turn research sessions',
    category: 'Sessions',
  },
  '/insights': {
    title: 'Citation Analytics',
    subtitle: 'Claim grounding coverage & attribution density',
    category: 'Analytics',
  },
  '/settings': {
    title: 'System Settings',
    subtitle: 'Dual AI provider routing & hardware telemetry',
    category: 'System',
  },
};

export const TopNav: React.FC<TopNavProps> = ({ onToggleMobileMenu }) => {
  const location = useLocation();
  const [isSupportOpen, setIsSupportOpen] = useState(false);
  const {
    isOnline,
    isGroqActive,
    isLoading,
    refetch,
  } = useHealth();
  const { resolvedTheme, toggleTheme } = useTheme();

  const currentMeta = routeTitles[location.pathname] || {
    title: 'DocuMind',
    subtitle: 'Document Intelligence & Verification',
    category: 'Platform',
  };

  return (
    <>
      <header className="h-16 border-b border-border-subtle bg-app/85 backdrop-blur-md px-3 sm:px-6 flex items-center justify-between z-20 shrink-0 select-none">
        {/* Page Title & Breadcrumb Hierarchy */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          {/* Mobile hamburger menu toggle */}
          {onToggleMobileMenu && (
            <button
              type="button"
              onClick={onToggleMobileMenu}
              className="p-1.5 min-w-[36px] min-h-[36px] md:hidden flex items-center justify-center rounded-lg text-content-secondary hover:text-content-primary hover:bg-surface-hover border border-transparent hover:border-border-subtle transition-all duration-120 active:scale-95 shrink-0"
              aria-label="Open navigation drawer"
            >
              <Menu className="w-5 h-5 text-content-primary" />
            </button>
          )}

          <span className="text-[10px] font-mono font-medium uppercase tracking-wider text-brand px-2 py-0.5 rounded bg-brand/15 border border-brand/30 shadow-xs shadow-brand/10 shrink-0">
            {currentMeta.category}
          </span>
          <div className="h-3.5 w-px bg-border-muted hidden sm:inline shrink-0" />
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2 min-w-0 truncate">
            <h1 className="text-sm font-semibold tracking-tight text-content-primary truncate">
              {currentMeta.title}
            </h1>
            <span className="text-content-muted hidden lg:inline text-xs shrink-0">•</span>
            <span className="text-xs text-content-secondary hidden lg:inline truncate max-w-xs xl:max-w-md">
              {currentMeta.subtitle}
            </span>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* Active AI Provider Capsule */}
          <div
            className={cn(
              'flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono border shadow-xs transition-colors',
              isOnline
                ? 'border-brand/30 bg-brand/5 text-content-primary'
                : 'border-border-muted bg-surface-primary text-content-secondary'
            )}
            title={
              isGroqActive
                ? 'Groq Cloud API (llama-3.3-70b-versatile) • Local Ollama Embeddings'
                : 'Local Ollama Engine (llama3.2:3b) • Local Embeddings'
            }
          >
            <span
              className={cn(
                'w-2 h-2 rounded-full',
                isOnline
                  ? isGroqActive
                    ? 'bg-brand shadow-sm shadow-brand/50'
                    : 'bg-status-success shadow-sm shadow-status-success/50'
                  : 'bg-status-error'
              )}
            />
            <span className="text-[11px] font-medium tracking-tight text-content-primary">
              {isGroqActive ? 'Groq Active' : 'Local Ollama'}
            </span>
          </div>

          {/* Divider */}
          <div className="h-4 w-px bg-border-subtle" />

          {/* Refresh Action */}
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg text-content-secondary hover:text-content-primary hover:bg-surface-hover border border-transparent hover:border-border-subtle transition-all duration-120 ease-standard active:scale-95 focus:outline-none focus-visible:ring-1 focus-visible:ring-brand"
            title="Refresh engine telemetry"
            aria-label="Refresh engine telemetry"
          >
            <RefreshCw className={cn('w-4 h-4 transition-transform', isLoading && 'animate-spin text-brand')} />
          </button>

          {/* Support / Contact Modal Trigger */}
          <button
            onClick={() => setIsSupportOpen(true)}
            className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg text-content-secondary hover:text-content-primary hover:bg-surface-hover border border-transparent hover:border-border-subtle transition-all duration-120 ease-standard active:scale-95 focus:outline-none focus-visible:ring-1 focus-visible:ring-brand"
            title="Help & Support"
            aria-label="Help & Support"
          >
            <HelpCircle className="w-4 h-4 text-content-secondary hover:text-brand transition-colors" />
          </button>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-2 min-w-[36px] min-h-[36px] flex items-center justify-center rounded-lg text-content-secondary hover:text-content-primary hover:bg-surface-hover border border-transparent hover:border-border-subtle transition-all duration-120 ease-standard active:scale-95 focus:outline-none focus-visible:ring-1 focus-visible:ring-brand"
            title={`Switch to ${resolvedTheme === 'dark' ? 'Light' : 'Dark'} mode`}
            aria-label="Toggle visual theme"
          >
            {resolvedTheme === 'dark' ? (
              <Sun className="w-4 h-4 text-content-secondary hover:text-brand transition-colors" />
            ) : (
              <Moon className="w-4 h-4 text-content-secondary hover:text-brand transition-colors" />
            )}
          </button>
        </div>
      </header>

      {/* Support / Feedback Dialog */}
      <SupportModal isOpen={isSupportOpen} onClose={() => setIsSupportOpen(false)} />
    </>
  );
};
