/**
 * Research Query Request Lifecycle Manager
 *
 * Implements deterministic multi-stage lifecycle tracking for long-running
 * local grounded inference queries with abort cancellation, single-flight
 * arbitration, and structured outcome classification.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryApi } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import { formatError, type FormattedError } from '@/utils/errors';
import type { QueryRequest, GroundedAnswer } from '@/types/api';

export type QueryLifecycleStatus =
  | 'idle'
  | 'submitting'
  | 'processing'
  | 'answer_received'
  | 'partially_answered'
  | 'abstained'
  | 'failed'
  | 'cancelled';

export interface UseResearchQueryResult {
  status: QueryLifecycleStatus;
  answer: GroundedAnswer | null;
  error: FormattedError | null;
  isSubmitting: boolean;
  isProcessing: boolean;
  isBusy: boolean;
  isAbstained: boolean;
  isPartial: boolean;
  isSuccess: boolean;
  submit: (request: QueryRequest) => Promise<GroundedAnswer | null>;
  cancel: () => void;
  reset: () => void;
}

export function useResearchQuery(): UseResearchQueryResult {
  const [status, setStatus] = useState<QueryLifecycleStatus>('idle');
  const [answer, setAnswer] = useState<GroundedAnswer | null>(null);
  const [error, setError] = useState<FormattedError | null>(null);

  const queryClient = useQueryClient();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Clean up any in-flight request when component unmounts
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  const isSubmitting = status === 'submitting';
  const isProcessing = status === 'processing';
  const isBusy = isSubmitting || isProcessing;
  const isAbstained = status === 'abstained';
  const isPartial = status === 'partially_answered';
  const isSuccess = status === 'answer_received' || isPartial || isAbstained;

  const cancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus('cancelled');
    setError({
      title: 'Query Cancelled',
      message: 'Inference request was cancelled by the user.',
      status: 0,
      isRetryable: true,
      isBusy: false,
    });
  }, []);

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus('idle');
    setAnswer(null);
    setError(null);
  }, []);

  const submit = useCallback(
    async (request: QueryRequest): Promise<GroundedAnswer | null> => {
      // Hardware Arbiter Safety: Prevent accidental duplicate submissions
      if (abortControllerRef.current || isBusy) {
        console.warn('[DocuMind] Blocked duplicate query submission while execution is in flight.');
        return null;
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setStatus('submitting');
      setError(null);
      setAnswer(null);

      try {
        // Transition to processing state
        setStatus('processing');

        const result = await queryApi.execute(request, controller.signal);

        // Discard result if cancelled while awaiting
        if (controller.signal.aborted) {
          setStatus('cancelled');
          return null;
        }

        setAnswer(result);

        // Classify outcome based on grounded confidence and abstention
        if (result.abstained || result.status === 'abstained') {
          setStatus('abstained');
        } else if (result.status === 'partially_answered' || result.confidence < 0.60) {
          setStatus('partially_answered');
        } else {
          setStatus('answer_received');
        }

        // If conversation ID was attached, invalidate detail cache so new turn is loaded
        if (request.conversation_id) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.conversations.detail(request.conversation_id),
          });
          queryClient.invalidateQueries({
            queryKey: queryKeys.conversations.all,
          });
        }

        return result;
      } catch (err: unknown) {
        if (controller.signal.aborted || (err as any)?.name === 'AbortError') {
          setStatus('cancelled');
          setError({
            title: 'Query Cancelled',
            message: 'Inference request was cancelled.',
            status: 0,
            isRetryable: true,
            isBusy: false,
          });
          return null;
        }

        const formatted = formatError(err);
        setError(formatted);
        setStatus('failed');
        return null;
      } finally {
        abortControllerRef.current = null;
      }
    },
    [isBusy, queryClient]
  );

  return {
    status,
    answer,
    error,
    isSubmitting,
    isProcessing,
    isBusy,
    isAbstained,
    isPartial,
    isSuccess,
    submit,
    cancel,
    reset,
  };
}
