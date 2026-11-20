/**
 * Backend-Driven Conversation State & Turn History Manager
 *
 * Coordinates active session selection, message chronological ordering,
 * persistent citation restoration, and session creation/deletion.
 */

import { useState, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useConversation, useConversations } from './useQueries';
import { useCreateConversation, useDeleteConversation } from './useMutations';
import { useResearchQuery } from './useResearchQuery';
import { queryKeys } from '@/services/queryKeys';
import { storage } from '@/utils/storage';
import type {
  ConversationResponse,
  ConversationDetailResponse,
  MessageResponse,
  GroundedAnswer,
} from '@/types/api';

export interface UseConversationStateResult {
  // Conversation List
  conversations: ConversationResponse[];
  isLoadingList: boolean;

  // Active Conversation
  activeConversationId: string | null;
  activeConversation: ConversationDetailResponse | undefined;
  messages: MessageResponse[];
  isLoadingActive: boolean;

  // Query / Research Execution
  researchState: ReturnType<typeof useResearchQuery>;

  // Actions
  selectConversation: (id: string | null) => void;
  createConversation: (title?: string) => Promise<string | null>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (question: string, documentIds?: string[]) => Promise<GroundedAnswer | null>;
  refreshActive: () => void;
}

export function useConversationState(
  initialConversationId?: string | null
): UseConversationStateResult {
  const queryClient = useQueryClient();

  // Initialize from parameter or fallback to last-opened session preference
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    if (initialConversationId !== undefined) {
      return initialConversationId;
    }
    return storage.getLastConversationId();
  });

  // Load conversation listing
  const listQuery = useConversations(0, 100);

  // Load active conversation thread
  const activeQuery = useConversation(activeConversationId, {
    enabled: !!activeConversationId,
  });

  // Mutations
  const createMutation = useCreateConversation();
  const deleteMutation = useDeleteConversation();

  // Research Query lifecycle
  const researchState = useResearchQuery();

  // Select a conversation and update local preference
  const selectConversation = useCallback((id: string | null) => {
    setActiveConversationId(id);
    storage.setLastConversationId(id);
  }, []);

  // Create new conversation
  const createConversation = useCallback(
    async (title?: string): Promise<string | null> => {
      try {
        const created = await createMutation.mutateAsync(title);
        setActiveConversationId(created.id);
        storage.setLastConversationId(created.id);
        return created.id;
      } catch (e) {
        console.error('[DocuMind] Failed to create conversation', e);
        return null;
      }
    },
    [createMutation]
  );

  // Delete conversation
  const deleteConversation = useCallback(
    async (id: string): Promise<void> => {
      await deleteMutation.mutateAsync(id);
      if (activeConversationId === id) {
        setActiveConversationId(null);
        storage.setLastConversationId(null);
      }
    },
    [deleteMutation, activeConversationId]
  );

  // Send research message attached to active conversation
  const sendMessage = useCallback(
    async (question: string, documentIds?: string[]): Promise<GroundedAnswer | null> => {
      let targetConvId = activeConversationId;

      // Auto-create conversation if none currently active
      if (!targetConvId) {
        const generatedTitle =
          question.length > 40 ? `${question.slice(0, 37)}...` : question;
        targetConvId = await createConversation(generatedTitle);
        if (!targetConvId) {
          throw new Error('Failed to initialize conversation session.');
        }
      }

      const result = await researchState.submit({
        question,
        document_ids: documentIds,
        conversation_id: targetConvId,
      });

      if (result) {
        // Refetch active conversation so the new message and citations appear
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.detail(targetConvId),
        });
        queryClient.invalidateQueries({
          queryKey: queryKeys.conversations.all,
        });
      }

      return result;
    },
    [activeConversationId, createConversation, researchState, queryClient]
  );

  // Sort messages strictly chronologically ascending
  const sortedMessages = useMemo(() => {
    if (!activeQuery.data?.messages) return [];
    return [...activeQuery.data.messages].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
  }, [activeQuery.data?.messages]);

  return {
    conversations: listQuery.data || [],
    isLoadingList: listQuery.isLoading,

    activeConversationId,
    activeConversation: activeQuery.data,
    messages: sortedMessages,
    isLoadingActive: activeQuery.isLoading,

    researchState,

    selectConversation,
    createConversation,
    deleteConversation,
    sendMessage,
    refreshActive: () => activeQuery.refetch(),
  };
}
