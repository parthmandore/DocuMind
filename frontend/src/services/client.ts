/**
 * HTTP Client Wrapper for DocuMind Backend API
 *
 * Enforces API contract, structured error normalization, request cancellation,
 * and controlled backoff for HTTP 503 (OllamaBusyError).
 */

export class ApiError extends Error {
  status: number;
  detail: string | Array<{ loc: (string | number)[]; msg: string; type: string }>;
  isBusy: boolean;

  constructor(status: number, detail: any, message?: string) {
    const detailString =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
        ? detail.map((d) => d.msg).join('; ')
        : 'API Request Failed';

    super(message || detailString);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.isBusy = status === 503;
  }
}

interface RequestOptions extends RequestInit {
  retryOnBusy?: boolean;
  maxBusyRetries?: number;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const {
    retryOnBusy = false,
    maxBusyRetries = 2,
    headers: customHeaders,
    ...restOptions
  } = options;

  const url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  let attempts = 0;
  const maxAttempts = retryOnBusy ? maxBusyRetries + 1 : 1;

  while (attempts < maxAttempts) {
    attempts++;

    try {
      const isFormData = restOptions.body instanceof FormData;

      const headers: HeadersInit = {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...customHeaders,
      };

      const response = await fetch(url, {
        ...restOptions,
        headers,
      });

      if (response.ok) {
        // Handle 204 No Content
        if (response.status === 204) {
          return {} as T;
        }

        // Return blob/binary if requested or stream
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/pdf') || contentType.includes('application/octet-stream')) {
          return (await response.blob()) as unknown as T;
        }

        return (await response.json()) as T;
      }

      // Parse error payload from FastAPI
      let errorDetail: any = 'An unknown server error occurred.';
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorJson;
      } catch {
        errorDetail = response.statusText || `HTTP ${response.status}`;
      }

      // Handle 503 (Local Model Busy / Memory Threshold)
      if (response.status === 503 && retryOnBusy && attempts < maxAttempts) {
        const backoffMs = Math.pow(2, attempts) * 1500; // 3s, 6s backoff
        await sleep(backoffMs);
        continue;
      }

      throw new ApiError(response.status, errorDetail);
    } catch (err) {
      if (err instanceof ApiError) {
        throw err;
      }

      // Handle network / connection dropped
      const isAbort = (err as any)?.name === 'AbortError';
      if (isAbort) {
        throw new ApiError(0, 'Request aborted by user.', 'Request aborted.');
      }

      throw new ApiError(
        0,
        'Cannot connect to local DocuMind backend. Ensure the server is running on http://127.0.0.1:8000.',
        (err as Error).message
      );
    }
  }

  throw new ApiError(503, 'Inference engine busy after maximum retries.');
}
