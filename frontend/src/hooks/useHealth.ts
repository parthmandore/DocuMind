import { useQuery } from '@tanstack/react-query';
import { healthApi } from '@/services/api';
import { queryKeys } from '@/services/queryKeys';
import type { HealthResponse } from '@/types/api';

export interface UseHealthResult {
  health: HealthResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isOnline: boolean;
  isHealthy: boolean;
  isDegraded: boolean;
  isOllamaConnected: boolean;
  activeProvider: 'ollama' | 'groq';
  isGroqActive: boolean;
  isGroqConfigured: boolean;
  generationStatus: string;
  refetch: () => void;
}

export function useHealth(pollIntervalMs = 10000): UseHealthResult {
  const { data, isLoading, isError, error, refetch } = useQuery<HealthResponse, Error>({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => healthApi.check(signal),
    refetchInterval: pollIntervalMs,
    staleTime: 5000,
    retry: 1,
  });

  const isOnline = !isError && !!data;
  const isHealthy = data?.status === 'healthy';
  const isDegraded = data?.status === 'degraded';
  const isOllamaConnected = data?.ollama_status === 'connected';
  const activeProvider = data?.active_provider || 'ollama';
  const isGroqActive = activeProvider === 'groq';
  const isGroqConfigured = !!data?.groq_configured;
  const generationStatus = data?.generation_provider_status || data?.ollama_status || 'unknown';

  return {
    health: data,
    isLoading,
    isError,
    error,
    isOnline,
    isHealthy,
    isDegraded,
    isOllamaConnected,
    activeProvider,
    isGroqActive,
    isGroqConfigured,
    generationStatus,
    refetch,
  };
}
