/**
 * Typed Domain Services for DocuMind Backend
 *
 * Implements client calls matching the Phase 5.0 API contract.
 */

import { apiClient } from './client';
import type {
  HealthResponse,
  DocumentResponse,
  DocumentUploadResponse,
  DocumentContentResponse,
  IndexingStatusResponse,
  ReindexResponse,
  JobResponse,
  SearchResponse,
  RetrievalMode,
  GroundedAnswer,
  QueryRequest,
  ConversationResponse,
  ConversationDetailResponse,
  AIProviderSettingsResponse,
  AIProviderType,
  InsightsResponse,
  ContactRequest,
  ContactResponse,
} from '@/types/api';

// --- Health & System API ---

export const healthApi = {
  check: (signal?: AbortSignal): Promise<HealthResponse> =>
    apiClient<HealthResponse>('/api/health', { signal }),
};

export const aiProviderApi = {
  get: (signal?: AbortSignal): Promise<AIProviderSettingsResponse> =>
    apiClient<AIProviderSettingsResponse>('/api/settings/ai-provider', { signal }),

  set: (provider: AIProviderType, signal?: AbortSignal): Promise<AIProviderSettingsResponse> =>
    apiClient<AIProviderSettingsResponse>('/api/settings/ai-provider', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider }),
      signal,
    }),
};

// --- Documents API ---

export const documentsApi = {
  upload: (file: File, signal?: AbortSignal): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient<DocumentUploadResponse>('/api/documents/upload', {
      method: 'POST',
      body: formData,
      signal,
    });
  },

  list: (skip = 0, limit = 100, signal?: AbortSignal): Promise<DocumentResponse[]> =>
    apiClient<DocumentResponse[]>(`/api/documents?skip=${skip}&limit=${limit}`, { signal }),

  get: (docId: string, signal?: AbortSignal): Promise<DocumentResponse> =>
    apiClient<DocumentResponse>(`/api/documents/${encodeURIComponent(docId)}`, { signal }),

  getContent: (docId: string, signal?: AbortSignal): Promise<DocumentContentResponse> =>
    apiClient<DocumentContentResponse>(`/api/documents/${encodeURIComponent(docId)}/content`, {
      signal,
    }),

  getFileUrl: (docId: string): string =>
    `/api/documents/${encodeURIComponent(docId)}/file`,

  downloadFile: (docId: string, signal?: AbortSignal): Promise<Blob> =>
    apiClient<Blob>(`/api/documents/${encodeURIComponent(docId)}/file`, { signal }),

  delete: (docId: string, signal?: AbortSignal): Promise<{ message: string }> =>
    apiClient<{ message: string }>(`/api/documents/${encodeURIComponent(docId)}`, {
      method: 'DELETE',
      signal,
    }),

  getIndexingStatus: (docId: string, signal?: AbortSignal): Promise<IndexingStatusResponse> =>
    apiClient<IndexingStatusResponse>(
      `/api/documents/${encodeURIComponent(docId)}/indexing-status`,
      { signal }
    ),

  reindex: (docId: string, signal?: AbortSignal): Promise<ReindexResponse> =>
    apiClient<ReindexResponse>(`/api/documents/${encodeURIComponent(docId)}/reindex`, {
      method: 'POST',
      signal,
    }),
};

// --- Processing Jobs API ---

export const jobsApi = {
  list: (skip = 0, limit = 50, signal?: AbortSignal): Promise<JobResponse[]> =>
    apiClient<JobResponse[]>(`/api/jobs?skip=${skip}&limit=${limit}`, { signal }),

  get: (jobId: string, signal?: AbortSignal): Promise<JobResponse> =>
    apiClient<JobResponse>(`/api/jobs/${encodeURIComponent(jobId)}`, { signal }),
};

// --- Search API ---

export interface SearchParams {
  q: string;
  mode?: RetrievalMode;
  top_k?: number;
  document_ids?: string[];
}

export const searchApi = {
  search: (params: SearchParams, signal?: AbortSignal): Promise<SearchResponse> => {
    const searchParams = new URLSearchParams();
    searchParams.set('q', params.q);
    if (params.mode) searchParams.set('mode', params.mode);
    if (params.top_k) searchParams.set('top_k', String(params.top_k));
    if (params.document_ids && params.document_ids.length > 0) {
      params.document_ids.forEach((id) => searchParams.append('document_ids', id));
    }
    return apiClient<SearchResponse>(`/api/search?${searchParams.toString()}`, { signal });
  },
};

// --- Grounded Query API (Research Workspace Core) ---

export const queryApi = {
  execute: (request: QueryRequest, signal?: AbortSignal): Promise<GroundedAnswer> =>
    apiClient<GroundedAnswer>('/api/query', {
      method: 'POST',
      body: JSON.stringify(request),
      signal,
      retryOnBusy: false, // Never auto-retry long-running inference requests
    }),
};

// --- Conversations API ---

export const conversationsApi = {
  create: (title?: string, signal?: AbortSignal): Promise<ConversationResponse> =>
    apiClient<ConversationResponse>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title || null }),
      signal,
    }),

  list: (
    skip = 0,
    limit = 50,
    search?: string,
    signal?: AbortSignal
  ): Promise<ConversationResponse[]> => {
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(limit),
    });
    if (search && search.trim()) {
      params.set('search', search.trim());
    }
    return apiClient<ConversationResponse[]>(
      `/api/conversations?${params.toString()}`,
      { signal }
    );
  },

  getDetails: (conversationId: string, signal?: AbortSignal): Promise<ConversationDetailResponse> =>
    apiClient<ConversationDetailResponse>(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      { signal }
    ),

  rename: (
    conversationId: string,
    title: string,
    signal?: AbortSignal
  ): Promise<ConversationResponse> =>
    apiClient<ConversationResponse>(
      `/api/conversations/${encodeURIComponent(conversationId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify({ title }),
        signal,
      }
    ),

  delete: (conversationId: string, signal?: AbortSignal): Promise<{ message: string }> =>
    apiClient<{ message: string }>(`/api/conversations/${encodeURIComponent(conversationId)}`, {
      method: 'DELETE',
      signal,
    }),
};

// --- Citation Analytics API (Phase 5.9) ---

export const analyticsApi = {
  getInsights: (signal?: AbortSignal): Promise<InsightsResponse> =>
    apiClient<InsightsResponse>('/api/analytics/insights', { signal }),
};

// --- Support & Feedback API ---

export const supportApi = {
  submitContact: (payload: ContactRequest, signal?: AbortSignal): Promise<ContactResponse> =>
    apiClient<ContactResponse>('/api/support/contact', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
};
