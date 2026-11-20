/**
 * Centralized Connection Status & Engine Diagnostics Manager
 *
 * Distinguishes between FastAPI backend health, Ollama inference connectivity,
 * hardware arbiter locks (503), and host system constraints.
 */

import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type { HealthResponse } from '@/types/api';

export type BackendConnectionState = 'HEALTHY' | 'DEGRADED' | 'OFFLINE';
export type OllamaConnectionState = 'CONNECTED' | 'UNREACHABLE' | 'UNKNOWN';
export type CompositeEngineState =
  | 'READY'
  | 'DEGRADED'
  | 'OFFLINE'
  | 'MODEL_BUSY'
  | 'LOW_STORAGE';

export interface UseConnectionStatusResult {
  health: HealthResponse | undefined;
  isLoading: boolean;
  isBackendOnline: boolean;
  isOllamaConnected: boolean;
  isModelBusy: boolean;
  isMemoryPressure: boolean;
  backendState: BackendConnectionState;
  ollamaState: OllamaConnectionState;
  compositeState: CompositeEngineState;
  statusMessage: string;
  setModelBusy: (busy: boolean) => void;
  checkConnection: () => Promise<void>;
}

export function useConnectionStatus(pollIntervalMs = 10000): UseConnectionStatusResult {
  const [isModelBusy, setIsModelBusy] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery<HealthResponse, Error>({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => healthApi.check(signal),
    refetchInterval: isModelBusy ? 5000 : pollIntervalMs, // Gentle poll when busy
    staleTime: 5000,
    retry: false, // Never retry health aggressively
  });

  const isBackendOnline = !isError && !!data;
  const isOllamaConnected = data?.ollama_status === 'connected';
  const isMemoryPressure = (data?.free_disk_gb ?? 10) < 2.0;

  const backendState: BackendConnectionState = useMemo(() => {
    if (!isBackendOnline) return 'OFFLINE';
    if (data?.status === 'degraded' || !isOllamaConnected) return 'DEGRADED';
    return 'HEALTHY';
  }, [isBackendOnline, data?.status, isOllamaConnected]);

  const ollamaState: OllamaConnectionState = useMemo(() => {
    if (!isBackendOnline) return 'UNKNOWN';
    return isOllamaConnected ? 'CONNECTED' : 'UNREACHABLE';
  }, [isBackendOnline, isOllamaConnected]);

  const compositeState: CompositeEngineState = useMemo(() => {
    if (!isBackendOnline) return 'OFFLINE';
    if (isModelBusy) return 'MODEL_BUSY';
    if (isMemoryPressure) return 'LOW_STORAGE';
    if (backendState === 'DEGRADED') return 'DEGRADED';
    return 'READY';
  }, [isBackendOnline, isModelBusy, isMemoryPressure, backendState]);

  const statusMessage = useMemo(() => {
    switch (compositeState) {
      case 'READY':
        return 'Local engine online and ready for research.';
      case 'MODEL_BUSY':
        return 'Inference arbiter currently processing another request.';
      case 'LOW_STORAGE':
        return `Low host disk space (${data?.free_disk_gb.toFixed(1)} GB remaining).`;
      case 'DEGRADED':
        return 'Backend online, but local Ollama inference is unreachable.';
      case 'OFFLINE':
      default:
        return 'Cannot connect to local DocuMind backend (127.0.0.1:8000).';
    }
  }, [compositeState, data?.free_disk_gb]);

  const checkConnection = useCallback(async () => {
    await refetch();
  }, [refetch]);

  return {
    health: data,
    isLoading,
    isBackendOnline,
    isOllamaConnected,
    isModelBusy,
    isMemoryPressure,
    backendState,
    ollamaState,
    compositeState,
    statusMessage,
    setModelBusy: setIsModelBusy,
    checkConnection,
  };
}
