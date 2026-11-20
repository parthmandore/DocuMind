/**
 * Global Safe Error Normalization Utilities
 *
 * Formats API, network, and application errors into user-friendly messages.
 * Strictly sanitizes internal filesystem paths, stack traces, and database internals.
 */

import { ApiError } from '@/services/client';

export interface FormattedError {
  title: string;
  message: string;
  status: number;
  isRetryable: boolean;
  isBusy: boolean;
}

// Regex to detect and sanitize Windows absolute paths (e.g. C:\Users\...) and unix-style repo paths
const PATH_REGEX = /(?:[a-zA-Z]:\\(?:[^\s\\/:*?"<>|]+\\)*[^\s\\/:*?"<>|]+|\/(?:home|var|tmp|backend|data)\/[^\s'"]+)/g;

// Regex to detect and strip Python tracebacks
const TRACEBACK_REGEX = /Traceback \(most recent call last\):[\s\S]+/g;

// Regex to strip raw SQL statements
const SQL_REGEX = /(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\s+[\s\S]+?(?:;|$)/gi;

/**
 * Sanitizes sensitive internal strings from error details.
 */
export function sanitizeErrorMessage(rawText: string): string {
  if (!rawText) return 'An unexpected error occurred.';

  let sanitized = rawText
    .replace(TRACEBACK_REGEX, 'An internal error occurred.')
    .replace(PATH_REGEX, '[local-path]')
    .replace(SQL_REGEX, '[database-query]');

  // Clean up excess whitespace
  sanitized = sanitized.replace(/\s+/g, ' ').trim();

  return sanitized || 'An unexpected error occurred.';
}

/**
 * Normalizes any error object into a user-friendly FormattedError.
 */
export function formatError(error: unknown): FormattedError {
  if (error instanceof ApiError) {
    const status = error.status;

    // HTTP 503: Hardware Arbiter / Ollama Busy
    if (status === 503) {
      return {
        title: 'Local Inference Engine Busy',
        message:
          'The local model hardware arbiter is currently executing an inference task. Please wait a moment and try again.',
        status,
        isRetryable: true,
        isBusy: true,
      };
    }

    // Status 0: Connection / Network Failure
    if (status === 0) {
      return {
        title: 'Backend Unreachable',
        message:
          'Unable to reach local DocuMind backend on http://127.0.0.1:8000. Ensure the FastAPI service is running.',
        status,
        isRetryable: true,
        isBusy: false,
      };
    }

    // HTTP 400: Bad Request / Security Rejection
    if (status === 400) {
      const rawMsg = typeof error.detail === 'string' ? error.detail : error.message;
      return {
        title: 'Invalid Request',
        message: sanitizeErrorMessage(rawMsg),
        status,
        isRetryable: false,
        isBusy: false,
      };
    }

    // HTTP 404: Not Found
    if (status === 404) {
      const rawMsg = typeof error.detail === 'string' ? error.detail : error.message;
      return {
        title: 'Resource Not Found',
        message: sanitizeErrorMessage(rawMsg),
        status,
        isRetryable: false,
        isBusy: false,
      };
    }

    // HTTP 422: Validation Error (FastAPI schema violation)
    if (status === 422) {
      let validationMsg = 'Request validation failed.';
      if (Array.isArray(error.detail)) {
        validationMsg = error.detail
          .map((d: any) => {
            const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : 'field';
            return `${field}: ${d.msg}`;
          })
          .join(', ');
      }
      return {
        title: 'Input Validation Failed',
        message: sanitizeErrorMessage(validationMsg),
        status,
        isRetryable: false,
        isBusy: false,
      };
    }

    // HTTP 500: Internal Server Error
    if (status === 500) {
      return {
        title: 'Server Error',
        message: 'An internal error occurred in the local backend. Check backend logs for details.',
        status,
        isRetryable: false,
        isBusy: false,
      };
    }

    // Generic fallback for other HTTP codes
    return {
      title: `Request Failed (HTTP ${status})`,
      message: sanitizeErrorMessage(error.message),
      status,
      isRetryable: false,
      isBusy: false,
    };
  }

  // Handle standard JavaScript Error
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return {
        title: 'Request Cancelled',
        message: 'The operation was cancelled by the user.',
        status: 0,
        isRetryable: false,
        isBusy: false,
      };
    }

    return {
      title: 'Application Error',
      message: sanitizeErrorMessage(error.message),
      status: -1,
      isRetryable: false,
      isBusy: false,
    };
  }

  // Fallback
  return {
    title: 'Unexpected Error',
    message: 'An unexpected issue occurred.',
    status: -1,
    isRetryable: false,
    isBusy: false,
  };
}
