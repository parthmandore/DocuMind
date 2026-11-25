/**
 * Asynchronous Document Processing & Background Job State Manager
 *
 * Implements controlled polling against `/api/jobs/{job_id}`, detects terminal
 * states (COMPLETED / FAILED), triggers metadata invalidation, and survives
 * navigation without orphaned network loops.
 */

import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jobsApi } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type { JobResponse, DocumentStatus, DocumentResponse } from '@/types/api';

export type JobStatusType = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface UseJobPollingOptions {
  pollIntervalMs?: number;
  documentId?: string;
  onComplete?: (job: JobResponse) => void;
  onError?: (job: JobResponse) => void;
  enabled?: boolean;
}

export interface UseJobPollingResult {
  job: JobResponse | undefined;
  isLoading: boolean;
  isPolling: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  status: JobStatusType | string;
  errorDetails: string | null;
  refetch: () => void;
}

export function isTerminalJobStatus(status: string | undefined): boolean {
  if (!status) return false;
  const upper = status.toUpperCase();
  return upper === 'COMPLETED' || upper === 'FAILED';
}

export function isDocumentProcessing(status: DocumentStatus | string | undefined): boolean {
  if (!status) return false;
  const upper = status.toUpperCase();
  return ['PENDING', 'PROCESSING', 'EXTRACTED', 'CHUNKED', 'EMBEDDING', 'INDEXED'].includes(
    upper
  );
}

/**
 * True when a document finished Stage A (extraction & chunking) and is searchable
 * via BM25, but Stage B vector embedding paused/failed (e.g. Ollama unreachable).
 */
export function isDocumentWaitingForEmbeddings(
  doc?: Pick<DocumentResponse, 'status' | 'error_message'> | null
): boolean {
  if (!doc) return false;
  return (doc.status || '').toUpperCase() === 'CHUNKED' && Boolean(doc.error_message);
}

/**
 * True only when a document has an active background pipeline running.
 * Prevents endless UI spinning and polling loops when Stage B is paused/failed.
 */
export function isDocumentActivelyProcessing(
  doc?: Pick<DocumentResponse, 'status' | 'error_message'> | null
): boolean {
  if (!doc) return false;
  if (isDocumentWaitingForEmbeddings(doc)) return false;
  return isDocumentProcessing(doc.status);
}

export function getDocumentStatusLabel(
  status: DocumentStatus | string | undefined,
  errorMessage?: string | null
): string {
  if (!status) return 'Unknown';
  switch (status.toUpperCase()) {
    case 'PENDING':
      return 'Queued for processing...';
    case 'PROCESSING':
      return 'Extracting text & layout...';
    case 'EXTRACTED':
      return 'Generating semantic chunks...';
    case 'CHUNKED':
      return errorMessage
        ? 'Lexical search ready (semantic embeddings paused)'
        : 'Computing vector embeddings...';
    case 'EMBEDDING':
      return 'Persisting vector index...';
    case 'INDEXED':
    case 'COMPLETED':
      return 'Ready for research';
    case 'FAILED':
      return 'Ingestion failed';
    default:
      return status;
  }
}

export function useJobPolling(
  jobId: string | undefined | null,
  options: UseJobPollingOptions = {}
): UseJobPollingResult {
  const {
    pollIntervalMs = 1500,
    documentId,
    onComplete,
    onError,
    enabled = true,
  } = options;

  const queryClient = useQueryClient();
  const handledTerminalRef = useRef<string | null>(null);

  const query = useQuery({
    queryKey: queryKeys.jobs.detail(jobId || ''),
    queryFn: ({ signal }) => {
      if (!jobId) throw new Error('Job ID is required for polling');
      return jobsApi.get(jobId, signal);
    },
    enabled: !!jobId && enabled,
    // Controlled polling: Poll if not terminal, cease polling immediately on COMPLETED or FAILED
    refetchInterval: (queryData) => {
      const currentJob = queryData.state.data;
      if (!currentJob) return pollIntervalMs;
      return isTerminalJobStatus(currentJob.status) ? false : pollIntervalMs;
    },
    refetchIntervalInBackground: false,
    staleTime: 0,
  });

  const job = query.data;
  const status = (job?.status || 'PENDING').toUpperCase() as JobStatusType;
  const isCompleted = status === 'COMPLETED';
  const isFailed = status === 'FAILED';
  const isPolling = !!jobId && enabled && !isTerminalJobStatus(status) && query.isFetching;

  // React to terminal transition exactly once per terminal occurrence
  useEffect(() => {
    if (!job || !isTerminalJobStatus(job.status)) {
      return;
    }

    const terminalKey = `${job.id}:${job.status}`;
    if (handledTerminalRef.current === terminalKey) {
      return;
    }
    handledTerminalRef.current = terminalKey;

    const targetDocId = documentId || job.document_id;

    // Invalidate document caches so UI shows completed chunks, tables, and status
    queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    if (targetDocId) {
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.detail(targetDocId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.content(targetDocId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.documents.indexingStatus(targetDocId),
      });
    }

    if (isCompleted && onComplete) {
      onComplete(job);
    } else if (isFailed && onError) {
      onError(job);
    }
  }, [job, isCompleted, isFailed, documentId, onComplete, onError, queryClient]);

  return {
    job,
    isLoading: query.isLoading,
    isPolling,
    isCompleted,
    isFailed,
    status,
    errorDetails: job?.error_details || null,
    refetch: query.refetch,
  };
}
