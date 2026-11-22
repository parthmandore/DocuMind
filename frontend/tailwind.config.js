/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        app: 'var(--bg-app)',
        background: 'var(--bg-app)',
        brand: {
          DEFAULT: 'var(--accent-primary)',
          hover: 'var(--accent-hover)',
          light: 'var(--accent-light)',
          muted: 'var(--accent-muted)',
          text: 'var(--accent-text)',
          lime: '#CDF22B',
          yellow: '#CDF22B',
        },
        surface: {
          primary: 'var(--bg-surface-primary)',
          secondary: 'var(--bg-surface-secondary)',
          elevated: 'var(--bg-surface-elevated)',
          hover: 'var(--bg-surface-hover)',
          50: '#22252B',
          100: '#191C21',
          200: '#111317',
          300: '#08090B',
          DEFAULT: 'var(--bg-surface-primary)',
        },
        sidebar: {
          DEFAULT: 'var(--bg-sidebar)',
          active: 'var(--accent-muted)',
          hover: 'rgba(205, 242, 43, 0.08)',
          border: 'var(--border-subtle)',
        },
        content: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          muted: 'var(--text-muted)',
        },
        status: {
          success: 'var(--status-success)',
          warning: 'var(--status-warning)',
          error: 'var(--status-error)',
          info: 'var(--status-info)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          muted: 'var(--border-muted)',
          focus: 'var(--border-focus)',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'Fira Code',
          'Cascadia Code',
          'Consolas',
          'monospace',
        ],
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
        enter: 'cubic-bezier(0, 0, 0.2, 1)',
        exit: 'cubic-bezier(0.4, 0, 1, 1)',
        expressive: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      transitionDuration: {
        '100': '100ms',
        '120': '120ms',
        '150': '150ms',
        '180': '180ms',
        '200': '200ms',
        '220': '220ms',
        '250': '250ms',
        '280': '280ms',
        '300': '300ms',
      },
      keyframes: {
        modalEnter: {
          '0%': { opacity: '0', transform: 'scale(0.96) translateY(4px)' },
          '100%': { opacity: '1', transform: 'scale(1) translateY(0)' },
        },
        dropdownEnter: {
          '0%': { opacity: '0', transform: 'scale(0.97) translateY(-4px)' },
          '100%': { opacity: '1', transform: 'scale(1) translateY(0)' },
        },
        toastEnter: {
          '0%': { opacity: '0', transform: 'translateY(16px) scale(0.97)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        settle: {
          '0%': { transform: 'scale(0.92)' },
          '50%': { transform: 'scale(1.05)' },
          '100%': { transform: 'scale(1)' },
        },
        shakeError: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%, 60%': { transform: 'translateX(-3px)' },
          '40%, 80%': { transform: 'translateX(3px)' },
        },
      },
      animation: {
        'modal-enter': 'modalEnter 200ms cubic-bezier(0, 0, 0.2, 1) forwards',
        'dropdown-enter': 'dropdownEnter 150ms cubic-bezier(0, 0, 0.2, 1) forwards',
        'toast-enter': 'toastEnter 220ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'settle': 'settle 240ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'shake-error': 'shakeError 240ms cubic-bezier(0.2, 0, 0, 1) forwards',
      },
    },
  },
  plugins: [],
};
