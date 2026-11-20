/**
 * Centralized Design Token System for DocuMind
 *
 * Sophisticated, Minimal, Premium Research Workspace
 * Brand Colors:
 * - 60% — Deep Black: #08090B (Main application background)
 * - 30% — Warm Ivory: #F5F3EF (Primary text and selected light surfaces)
 * - 10% — Electric Lime: #CDF22B (Primary accent and interactive highlights)
 */

export const tokens = {
  colors: {
    dark: {
      bgApp: '#08090B',
      bgSidebar: '#08090B',
      bgSurfacePrimary: '#111317',
      bgSurfaceSecondary: '#191C21',
      bgSurfaceElevated: '#191C21',
      bgSurfaceHover: '#22252B',
      textPrimary: '#F5F3EF',
      textSecondary: '#A6A49E',
      textMuted: '#777873',
      borderSubtle: '#292C32',
      borderMuted: '#3D424B',
      borderFocus: '#CDF22B',
      accentPrimary: '#CDF22B',
      accentHover: '#BAE01E',
      accentLight: '#DAF557',
      accentMuted: 'rgba(205, 242, 43, 0.15)',
      accentText: '#08090B',
      statusSuccess: '#10B981',
      statusWarning: '#F59E0B',
      statusError: '#EF4444',
      statusInfo: '#38BDF8',
    },
    light: {
      bgApp: '#F7F6F2',
      bgSidebar: '#EDEAE3',
      bgSurfacePrimary: '#FFFFFF',
      bgSurfaceSecondary: '#F2EFE9',
      bgSurfaceElevated: '#FFFFFF',
      bgSurfaceHover: '#E5E2DA',
      textPrimary: '#08090B',
      textSecondary: '#55565B',
      textMuted: '#777873',
      borderSubtle: '#DCD9D0',
      borderMuted: '#C5C1B6',
      borderFocus: '#CDF22B',
      accentPrimary: '#CDF22B',
      accentHover: '#BAE01E',
      accentLight: '#DAF557',
      accentMuted: 'rgba(205, 242, 43, 0.12)',
      accentText: '#08090B',
      statusSuccess: '#059669',
      statusWarning: '#D97706',
      statusError: '#DC2626',
      statusInfo: '#0284C7',
    },
  },
  typography: {
    fontSans:
      "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    fontMono:
      "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",
    headingScale: {
      h1: 'text-2xl sm:text-3xl font-semibold tracking-tight',
      h2: 'text-xl sm:text-2xl font-semibold tracking-tight',
      h3: 'text-lg font-semibold tracking-tight',
      h4: 'text-base font-medium',
      h5: 'text-xs font-semibold uppercase tracking-wider',
    },
    bodyScale: {
      lg: 'text-base leading-relaxed',
      base: 'text-sm leading-normal',
      sm: 'text-xs leading-normal',
      xs: 'text-[11px] leading-tight',
    },
  },
  spacing: {
    xs: '0.25rem', // 4px
    sm: '0.5rem', // 8px
    md: '1rem', // 16px
    lg: '1.5rem', // 24px
    xl: '2rem', // 32px
    xxl: '3rem', // 48px
  },
  radius: {
    sm: 'rounded', // 4px
    md: 'rounded-md', // 6px
    lg: 'rounded-lg', // 8px
    xl: 'rounded-xl', // 12px
    full: 'rounded-full', // 9999px
  },
  shadows: {
    subtle: 'shadow-sm',
    card: 'shadow-md shadow-black/20 dark:shadow-black/40',
    elevated: 'shadow-lg shadow-black/30 dark:shadow-black/60',
    dialog: 'shadow-2xl shadow-black/40 dark:shadow-black/80',
  },
  layout: {
    sidebarWidth: '16rem', // 256px / w-64
    sidebarCollapsedWidth: '4rem', // 64px / w-16
    topNavHeight: '4rem', // 64px / h-16
    contentMaxWidth: '80rem', // 1280px / max-w-7xl
    panelPadding: '1.5rem', // 24px / p-6
  },
  motion: {
    durations: {
      instant: '100ms', // Button feedback, click response
      fast: '150ms', // Hover states, icon transitions, tooltips
      normal: '200ms', // Dropdowns, modals, tabs, citations
      moderate: '250ms', // Sidebar width transitions, drawers
      deliberate: '300ms', // Major route/layout transitions
    },
    easings: {
      standard: 'cubic-bezier(0.2, 0, 0, 1)', // Snappy general interaction
      enter: 'cubic-bezier(0, 0, 0.2, 1)', // Smooth deceleration on entry
      exit: 'cubic-bezier(0.4, 0, 1, 1)', // Fast acceleration on exit
      expressive: 'cubic-bezier(0.34, 1.56, 0.64, 1)', // Tactile overshoot / spring
    },
    hitTargets: {
      minTouch: '44px', // WCAG / Fitts's law touch target minimum
      standardIcon: '36px', // Comfortable icon button bounding box
      compactIcon: '32px', // Compact inline action target
    },
  },
} as const;
