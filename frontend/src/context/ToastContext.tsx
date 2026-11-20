import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Info,
  X,
} from 'lucide-react';
import { cn } from '@/utils/cn';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
  createdAt: number;
}

export interface ToastOptions {
  title?: string;
  duration?: number;
}

export interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (type: ToastType, message: string, options?: ToastOptions) => string;
  dismissToast: (id: string) => void;
  success: (message: string, options?: ToastOptions) => string;
  error: (message: string, options?: ToastOptions) => string;
  warning: (message: string, options?: ToastOptions) => string;
  info: (message: string, options?: ToastOptions) => string;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const MAX_TOASTS = 5;
const DEFAULT_DURATION: Record<ToastType, number> = {
  success: 4000,
  info: 4000,
  warning: 5000,
  error: 6000,
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  const dismissToast = useCallback((id: string) => {
    // Clear timer if exists
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string, options?: ToastOptions): string => {
      const now = Date.now();
      const id = `${type}-${now}-${Math.random().toString(36).slice(2, 7)}`;
      const duration = options?.duration ?? DEFAULT_DURATION[type];

      setToasts((prev) => {
        // Prevent duplicate messages queued within 2 seconds
        const duplicate = prev.find(
          (t) => t.message === message && t.type === type && now - t.createdAt < 2000
        );
        if (duplicate) {
          return prev;
        }

        const newToast: ToastItem = {
          id,
          type,
          title: options?.title,
          message,
          duration,
          createdAt: now,
        };

        const updated = [...prev, newToast];
        if (updated.length > MAX_TOASTS) {
          // Drop oldest
          const dropped = updated.shift();
          if (dropped) {
            const oldTimer = timersRef.current.get(dropped.id);
            if (oldTimer) clearTimeout(oldTimer);
          }
        }
        return updated;
      });

      // Auto dismissal
      if (duration > 0) {
        const timer = setTimeout(() => {
          dismissToast(id);
        }, duration);
        timersRef.current.set(id, timer);
      }

      return id;
    },
    [dismissToast]
  );

  const success = useCallback(
    (message: string, options?: ToastOptions) => addToast('success', message, options),
    [addToast]
  );
  const error = useCallback(
    (message: string, options?: ToastOptions) => addToast('error', message, options),
    [addToast]
  );
  const warning = useCallback(
    (message: string, options?: ToastOptions) => addToast('warning', message, options),
    [addToast]
  );
  const info = useCallback(
    (message: string, options?: ToastOptions) => addToast('info', message, options),
    [addToast]
  );

  return (
    <ToastContext.Provider
      value={{
        toasts,
        addToast,
        dismissToast,
        success,
        error,
        warning,
        info,
      }}
    >
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextValue => {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
};

// =============================================================================
// Toast Container & Render Component
// =============================================================================

const toastStyles: Record<
  ToastType,
  {
    icon: React.ReactNode;
    border: string;
    bg: string;
    iconColor: string;
    badgeText: string;
  }
> = {
  success: {
    icon: <CheckCircle2 className="w-5 h-5 shrink-0" />,
    border: 'border-status-success/30',
    bg: 'bg-surface-primary',
    iconColor: 'text-status-success',
    badgeText: 'Success',
  },
  error: {
    icon: <AlertOctagon className="w-5 h-5 shrink-0" />,
    border: 'border-status-error/40',
    bg: 'bg-surface-primary',
    iconColor: 'text-status-error',
    badgeText: 'Error',
  },
  warning: {
    icon: <AlertTriangle className="w-5 h-5 shrink-0" />,
    border: 'border-status-warning/40',
    bg: 'bg-surface-primary',
    iconColor: 'text-status-warning',
    badgeText: 'Notice',
  },
  info: {
    icon: <Info className="w-5 h-5 shrink-0" />,
    border: 'border-brand/40',
    bg: 'bg-surface-primary',
    iconColor: 'text-brand',
    badgeText: 'Info',
  },
};

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notification Center"
      role="region"
      className="fixed top-20 right-5 z-50 flex flex-col gap-2.5 max-w-sm sm:max-w-md w-full pointer-events-none px-4 sm:px-0"
    >
      {toasts.map((toast) => {
        const style = toastStyles[toast.type];

        return (
          <div
            key={toast.id}
            role={toast.type === 'error' ? 'alert' : 'status'}
            className={cn(
              'pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-xl',
              'backdrop-blur-md animate-toast-enter transform-gpu',
              style.bg,
              style.border
            )}
          >
            <div className={cn('mt-0.5', style.iconColor)}>{style.icon}</div>

            <div className="flex-1 min-w-0 pr-1">
              <div className="flex items-center gap-2 mb-0.5">
                {toast.title ? (
                  <span className="text-xs font-bold text-content-primary">
                    {toast.title}
                  </span>
                ) : (
                  <span
                    className={cn(
                      'text-[10px] font-mono font-bold uppercase tracking-wider',
                      style.iconColor
                    )}
                  >
                    {style.badgeText}
                  </span>
                )}
              </div>
              <p className="text-xs text-content-secondary leading-relaxed break-words">
                {toast.message}
              </p>
            </div>

            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              className="min-w-[36px] min-h-[36px] p-2 flex items-center justify-center rounded-lg text-content-muted hover:text-content-primary hover:bg-surface-secondary transition-colors shrink-0 active:scale-95"
              aria-label="Close notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
