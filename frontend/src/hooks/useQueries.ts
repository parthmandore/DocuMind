/**
 * Reusable TanStack Query Hooks for DocuMind
 *
 * Implements deterministic query data fetching, caching, and state accessors.
 */

import { useQuery, type UseQueryOptions, type UseQueryResult } from '@tanstack/react-query';
import { documentsApi, jobsApi, searchApi, conversationsApi, analyticsApi, type SearchParams } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type {
  DocumentResponse,
  DocumentContentResponse,
  IndexingStatusResponse,
  JobResponse,
  SearchResponse,
  ConversationResponse,
  ConversationDetailResponse,
  InsightsResponse,
} from '@/types/api';

// --- Document Queries ---

export function useDocuments(
  skip = 0,
  limit = 100,
  options?: Partial<UseQueryOptions<DocumentResponse[], Error>>
): UseQueryResult<DocumentResponse[], Error> {
  return useQuery({
    queryKey: queryKeys.documents.list(skip, limit),
    queryFn: ({ signal }) => documentsApi.list(skip, limit, signal),
    staleTime: 30000,
    ...options,
  });
}

export function useDocument(
  docId: string | undefined | null,
  options?: Partial<UseQueryOptions<DocumentResponse, Error>>
): UseQueryResult<DocumentResponse, Error> {
  return useQuery({
    queryKey: queryKeys.documents.detail(docId || ''),
    queryFn: ({ signal }) => {
      if (!docId) throw new Error('Document ID is required');
      return documentsApi.get(docId, signal);
    },
    enabled: !!docId && (options?.enabled ?? true),
    staleTime: 60000,
    ...options,
  });
}

export function useDocumentContent(
  docId: string | undefined | null,
  options?: Partial<UseQueryOptions<DocumentContentResponse, Error>>
): UseQueryResult<DocumentContentResponse, Error> {
  return useQuery({
    queryKey: queryKeys.documents.content(docId || ''),
    queryFn: ({ signal }) => {
      if (!docId) throw new Error('Document ID is required');
      return documentsApi.getContent(docId, signal);
    },
    enabled: !!docId && (options?.enabled ?? true),
    staleTime: 120000,
    ...options,
  });
}

export function useIndexingStatus(
  docId: string | undefined | null,
  options?: Partial<UseQueryOptions<IndexingStatusResponse, Error>>
): UseQueryResult<IndexingStatusResponse, Error> {
  return useQuery({
    queryKey: queryKeys.documents.indexingStatus(docId || ''),
    queryFn: ({ signal }) => {
      if (!docId) throw new Error('Document ID is required');
      return documentsApi.getIndexingStatus(docId, signal);
    },
    enabled: !!docId && (options?.enabled ?? true),
    staleTime: 10000,
    ...options,
  });
}

// --- Background Job Queries ---

export function useJobs(
  skip = 0,
  limit = 50,
  options?: Partial<UseQueryOptions<JobResponse[], Error>>
): UseQueryResult<JobResponse[], Error> {
  return useQuery({
    queryKey: queryKeys.jobs.list(skip, limit),
    queryFn: ({ signal }) => jobsApi.list(skip, limit, signal),
    staleTime: 5000,
    ...options,
  });
}

export function useJob(
  jobId: string | undefined | null,
  options?: Partial<UseQueryOptions<JobResponse, Error>>
): UseQueryResult<JobResponse, Error> {
  return useQuery({
    queryKey: queryKeys.jobs.detail(jobId || ''),
    queryFn: ({ signal }) => {
      if (!jobId) throw new Error('Job ID is required');
      return jobsApi.get(jobId, signal);
    },
    enabled: !!jobId && (options?.enabled ?? true),
    ...options,
  });
}

// --- Search Queries ---

export function useSearch(
  params: SearchParams,
  options?: Partial<UseQueryOptions<SearchResponse, Error>>
): UseQueryResult<SearchResponse, Error> {
  const isSearchValid = !!params.q && params.q.trim().length > 0;

  return useQuery({
    queryKey: queryKeys.search(params),
    queryFn: ({ signal }) => searchApi.search(params, signal),
    enabled: isSearchValid && (options?.enabled ?? true),
    staleTime: 60000,
    ...options,
  });
}

// --- Conversation Queries ---

export function useConversations(
  skip = 0,
  limit = 50,
  search?: string,
  options?: Partial<UseQueryOptions<ConversationResponse[], Error>>
): UseQueryResult<ConversationResponse[], Error> {
  return useQuery({
    queryKey: queryKeys.conversations.list(skip, limit, search),
    queryFn: ({ signal }) => conversationsApi.list(skip, limit, search, signal),
    staleTime: 15000,
    ...options,
  });
}

export function useConversation(
  conversationId: string | undefined | null,
  options?: Partial<UseQueryOptions<ConversationDetailResponse, Error>>
): UseQueryResult<ConversationDetailResponse, Error> {
  return useQuery({
    queryKey: queryKeys.conversations.detail(conversationId || ''),
    queryFn: ({ signal }) => {
      if (!conversationId) throw new Error('Conversation ID is required');
      return conversationsApi.getDetails(conversationId, signal);
    },
    enabled: !!conversationId && (options?.enabled ?? true),
    staleTime: 10000,
    ...options,
  });
}

// --- Citation Analytics & Insights (Phase 5.9) ---

export function useInsights(
  options?: Partial<UseQueryOptions<InsightsResponse, Error>>
): UseQueryResult<InsightsResponse, Error> {
  return useQuery({
    queryKey: queryKeys.insights,
    queryFn: ({ signal }) => analyticsApi.getInsights(signal),
    staleTime: 30000,
    ...options,
  });
}
