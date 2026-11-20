/**
 * DocuMind Centralized Query Key Factory
 *
 * Provides strictly-typed, hierarchical query keys for TanStack Query
 * to ensure deterministic cache invalidation and query deduplication.
 */

import type { RetrievalMode } from '@/types/api';

export interface SearchQueryKeyParams {
  q: string;
  mode?: RetrievalMode;
  top_k?: number;
  document_ids?: string[];
}

export const queryKeys = {
  // System Health & Engine Diagnostics
  health: ['system-health'] as const,
  aiProvider: ['ai-provider-settings'] as const,

  // Documents
  documents: {
    all: ['documents'] as const,
    lists: () => [...queryKeys.documents.all, 'list'] as const,
    list: (skip = 0, limit = 100) =>
      [...queryKeys.documents.lists(), { skip, limit }] as const,
    details: () => [...queryKeys.documents.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.documents.details(), id] as const,
    content: (id: string) => [...queryKeys.documents.detail(id), 'content'] as const,
    indexingStatus: (id: string) =>
      [...queryKeys.documents.detail(id), 'indexing-status'] as const,
  },

  // Ingestion Processing Jobs
  jobs: {
    all: ['jobs'] as const,
    lists: () => [...queryKeys.jobs.all, 'list'] as const,
    list: (skip = 0, limit = 50) =>
      [...queryKeys.jobs.lists(), { skip, limit }] as const,
    details: () => [...queryKeys.jobs.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.jobs.details(), id] as const,
  },

  // Document Search
  search: (params: SearchQueryKeyParams) =>
    ['search', { ...params, document_ids: params.document_ids?.slice().sort() }] as const,

  // Stateful Conversations & Research Threads
  conversations: {
    all: ['conversations'] as const,
    lists: () => [...queryKeys.conversations.all, 'list'] as const,
    list: (skip = 0, limit = 50, search?: string) =>
      [...queryKeys.conversations.lists(), { skip, limit, search }] as const,
    details: () => [...queryKeys.conversations.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.conversations.details(), id] as const,
    messages: (id: string) => [...queryKeys.conversations.detail(id), 'messages'] as const,
  },

  // Citation Analytics & Grounding Insights (Phase 5.9)
  insights: ['analytics-insights'] as const,
};
