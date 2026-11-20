/**
 * Reusable TanStack Query Mutation Hooks for DocuMind
 *
 * Implements stateful mutations with atomic cache updates, deterministic
 * invalidation, duplicate prevention, and non-corrupting error states.
 */

import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { documentsApi, conversationsApi, queryApi } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type {
  DocumentUploadResponse,
  ReindexResponse,
  ConversationResponse,
  QueryRequest,
  GroundedAnswer,
} from '@/types/api';

// --- Document Mutations ---

export function useUploadDocument(): UseMutationResult<
  DocumentUploadResponse,
  Error,
  File
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: (data) => {
      // Invalidate documents list so the new pending/processing item appears
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
      // Invalidate background jobs
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
      // Pre-seed detail query if needed
      if (data.document?.id) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.documents.detail(data.document.id),
        });
      }
    },
  });
}

export function useDeleteDocument(): UseMutationResult<
  { message: string },
  Error,
  string
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (docId: string) => documentsApi.delete(docId),
    onSuccess: (_data, docId) => {
      // Invalidate all document lists
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
      // Remove detail & content caches immediately
      queryClient.removeQueries({ queryKey: queryKeys.documents.detail(docId) });
      queryClient.removeQueries({ queryKey: queryKeys.documents.content(docId) });
      queryClient.removeQueries({
        queryKey: queryKeys.documents.indexingStatus(docId),
      });
    },
  });
}

export function useReindexDocument(): UseMutationResult<
  ReindexResponse,
  Error,
  string
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (docId: string) => documentsApi.reindex(docId),
    onSuccess: (_data, docId) => {
      // Invalidate detail and indexing status
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.detail(docId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.indexingStatus(docId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    },
  });
}

// --- Conversation Mutations ---

export function useCreateConversation(): UseMutationResult<
  ConversationResponse,
  Error,
  string | undefined
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (title?: string) => conversationsApi.create(title),
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
      // Pre-seed detail cache with empty turn history
      queryClient.setQueryData(queryKeys.conversations.detail(newConv.id), {
        id: newConv.id,
        title: newConv.title,
        created_at: newConv.created_at,
        updated_at: newConv.updated_at,
        messages: [],
      });
    },
  });
}

export function useRenameConversation(): UseMutationResult<
  ConversationResponse,
  Error,
  { id: string; title: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      conversationsApi.rename(id, title),
    onSuccess: (updatedConv) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.conversations.detail(updatedConv.id),
      });
    },
  });
}

export function useDeleteConversation(): UseMutationResult<
  { message: string },
  Error,
  string
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (conversationId: string) =>
      conversationsApi.delete(conversationId),
    onSuccess: (_data, conversationId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations.all });
      queryClient.removeQueries({
        queryKey: queryKeys.conversations.detail(conversationId),
      });
      queryClient.removeQueries({
        queryKey: queryKeys.conversations.messages(conversationId),
      });
    },
  });
}

// --- Grounded Query & Inference Mutations ---

export function useExecuteQuery(): UseMutationResult<
  GroundedAnswer,
  Error,
  QueryRequest
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: QueryRequest) => queryApi.execute(request),
    onSuccess: (data, variables) => {
      // Invalidate conversation details and messages if attached
      const convId = variables.conversation_id || data.conversation_id;
      if (convId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.detail(convId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.messages(convId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.all,
        });
      }
      // Also invalidate insights analytics because new query & citations were generated
      queryClient.invalidateQueries({
        queryKey: queryKeys.insights,
      });
    },
  });
}
