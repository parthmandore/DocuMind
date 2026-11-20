import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertOctagon, RotateCcw, Home } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Keep full error and stack trace in development console logs for developers
    console.error('DocuMind UI Uncaught Error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReload = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  private handleGoHome = (): void => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/';
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const isDev = import.meta.env.DEV;

      return (
        <div className="min-h-screen bg-app flex items-center justify-center p-6 text-content-primary">
          <div className="max-w-lg w-full bg-surface-primary border border-border-subtle rounded-2xl p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-status-error/10 border border-status-error/20 flex items-center justify-center text-status-error shrink-0">
                <AlertOctagon className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h1 className="text-lg font-bold text-content-primary">
                  Something went wrong
                </h1>
                <p className="text-xs text-content-secondary leading-relaxed">
                  An unexpected error occurred while rendering this interface.
                  Your documents and database records remain safe and unaffected.
                </p>
              </div>
            </div>

            {/* Sanitized user-facing message */}
            <div className="p-3.5 bg-surface-secondary border border-border-subtle rounded-xl text-xs text-content-secondary space-y-1">
              <span className="font-semibold text-content-primary block">
                Error Summary:
              </span>
              <p className="font-mono text-[11px] text-status-error break-words">
                {this.state.error?.message || 'An unexpected rendering error occurred.'}
              </p>
            </div>

            {/* In DEV mode only, show sanitized stack trace for the local developer */}
            {isDev && this.state.errorInfo?.componentStack && (
              <details className="text-xs text-content-secondary border border-border-subtle rounded-lg p-2.5 bg-surface-secondary/40">
                <summary className="cursor-pointer hover:text-content-primary font-medium text-[11px] text-content-muted">
                  Development Component Stack (Dev Mode Only)
                </summary>
                <pre className="mt-2 p-2 bg-surface-secondary rounded text-[10px] overflow-x-auto text-content-muted font-mono leading-tight">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div className="pt-2 flex flex-wrap items-center justify-end gap-3">
              <Button
                variant="secondary"
                size="md"
                onClick={this.handleGoHome}
                icon={<Home className="w-4 h-4" />}
              >
                Back to Dashboard
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={this.handleReload}
                icon={<RotateCcw className="w-4 h-4" />}
              >
                Reload Application
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
