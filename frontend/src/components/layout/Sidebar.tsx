import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Files,
  Sparkles,
  MessageSquare,
  BarChart2,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Cloud,
  X,
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { useHealth } from '@/hooks/useHealth';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  name: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Documents', to: '/documents', icon: Files },
  { name: 'Research Workspace', to: '/research', icon: Sparkles },
  { name: 'Conversations', to: '/conversations', icon: MessageSquare },
  { name: 'Citation Analytics', to: '/insights', icon: BarChart2 },
  { name: 'System Settings', to: '/settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
}) => {
  const { isOnline, isGroqActive } = useHealth();

  return (
    <>
      {/* Mobile Drawer Overlay Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'flex flex-col bg-sidebar border-r border-border-subtle transition-all duration-250 ease-standard select-none z-50 shrink-0 h-screen',
          // Mobile responsive: off-canvas drawer on small screens
          'fixed inset-y-0 left-0 md:relative',
          mobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0',
          // Desktop width handling
          collapsed ? 'md:w-16' : 'md:w-64',
          'w-64'
        )}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between h-16 px-4 border-b border-border-subtle">
          <NavLink
            to="/"
            onClick={() => onCloseMobile?.()}
            className="flex items-center gap-3 overflow-hidden group focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand rounded-lg"
            title="DocuMind Dashboard"
          >
            {/* Brand Mark with Accent Highlight */}
            <div className="w-8 h-8 rounded-lg bg-brand/15 border border-brand/40 flex items-center justify-center text-brand shrink-0 shadow-sm shadow-brand/20 transition-transform group-hover:scale-105">
              <span className="font-bold text-base font-sans tracking-tight text-brand">D</span>
            </div>
            {(!collapsed || mobileOpen) && (
              <div className="flex flex-col truncate">
                <span className="font-semibold text-sm tracking-tight text-content-primary group-hover:text-white transition-colors">
                  DocuMind
                </span>
                <span className="text-[10px] font-mono tracking-wider uppercase text-content-muted">
                  Document Intelligence
                </span>
              </div>
            )}
          </NavLink>

          {/* Close drawer button on mobile */}
          {onCloseMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              className="md:hidden p-1.5 rounded-lg text-content-muted hover:text-content-primary hover:bg-surface-secondary active:scale-95"
              aria-label="Close navigation drawer"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation List */}
        <nav className="flex-1 px-2.5 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => onCloseMobile?.()}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 min-h-[40px] rounded-lg text-sm font-medium transition-all duration-120 ease-standard active:scale-[0.98] group relative select-none',
                  isActive
                    ? 'bg-brand/10 border border-brand/25 text-content-primary shadow-xs font-semibold'
                    : 'border border-transparent text-content-secondary hover:text-content-primary hover:bg-surface-hover/80'
                )
              }
              title={collapsed ? item.name : undefined}
            >
              {({ isActive }) => (
                <>
                  {/* Left Accent Bar for Active Navigation State */}
                  {isActive && (
                    <span
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-brand rounded-r-full shadow-sm shadow-brand/50"
                      aria-hidden="true"
                    />
                  )}

                  <Icon
                    className={cn(
                      'w-4 h-4 shrink-0 transition-colors',
                      isActive ? 'text-brand' : 'text-content-muted group-hover:text-content-primary'
                    )}
                  />
                  {!collapsed && (
                    <span className="truncate flex-1 tracking-tight">{item.name}</span>
                  )}
                  {!collapsed && item.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] rounded bg-brand/12 text-brand font-mono font-medium border border-brand/25">
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Engine Status Pod */}
      <div className="p-3 border-t border-border-subtle bg-surface-primary/60">
        {!collapsed ? (
          <div className="flex items-center justify-between px-2 py-1.5 rounded-lg border border-border-subtle bg-surface-secondary/70 text-xs">
            <div className="flex items-center gap-2 truncate">
              {isGroqActive ? (
                <Cloud className="w-3.5 h-3.5 text-brand shrink-0" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5 text-brand shrink-0" />
              )}
              <div className="flex flex-col truncate">
                <span className="text-[11px] font-medium text-content-primary truncate">
                  {isGroqActive ? 'Groq Cloud' : 'Local Ollama'}
                </span>
                <span className="text-[9px] font-mono text-content-muted truncate uppercase tracking-wider">
                  {isGroqActive ? 'LLaMA 3.3 70B' : 'LLaMA 3.2 3B'}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 shrink-0 pl-1">
              <span
                className={cn(
                  'w-2 h-2 rounded-full',
                  isOnline
                    ? isGroqActive
                      ? 'bg-brand ring-2 ring-brand/30'
                      : 'bg-status-success ring-2 ring-status-success/30'
                    : 'bg-status-error ring-2 ring-status-error/30'
                )}
                title={isOnline ? 'System online' : 'Backend offline'}
              />
            </div>
          </div>
        ) : (
          <div
            className="flex justify-center py-1"
            title={isGroqActive ? 'Groq Cloud Active' : 'Local Ollama Active'}
          >
            <span
              className={cn(
                'w-2.5 h-2.5 rounded-full ring-2',
                isOnline
                  ? isGroqActive
                    ? 'bg-brand ring-brand/30'
                    : 'bg-status-success ring-status-success/30'
                  : 'bg-status-error ring-status-error/30'
              )}
            />
          </div>
        )}
      </div>

      {/* Collapse Toggle Button (Fitts's Law 44px hit target) */}
      <button
        onClick={onToggleCollapse}
        className="h-11 min-h-[44px] flex items-center justify-center border-t border-border-subtle text-content-muted hover:text-content-primary hover:bg-surface-secondary transition-all duration-120 ease-standard active:scale-[0.98] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
      </button>
    </aside>
    </>
  );
};
